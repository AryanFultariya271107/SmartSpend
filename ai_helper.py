"""ai_helper.py - Google Gemini API Structured JSON Handler & Multi-Turn Voice/Text Engine.

Uses the official `google-genai` SDK (`from google import genai`, `from google.genai import types`).
Targets `gemini-2.5-flash` with automatic fallback to `gemini-2.5-flash-lite` and `gemini-2.0-flash`.
Provides:
- process_ai_text: Multi-turn natural language parser & conversational financial coach
- process_ai_audio: Multimodal audio speech-to-intent engine for Hindi, English, and Hinglish
- check_ai_status: Verifies Gemini API configuration, connectivity, and SDK installation
- handle_ai_chat: Backwards-compatible router
- _offline_fallback: Comprehensive multi-action offline fallback parser
"""

import calendar
import datetime
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

# Explicitly load .env relative to the spendcalm project directory
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env", override=True)
logger = logging.getLogger(__name__)

ALLOWED_MOOD_TAGS = {"Essential", "Craving", "Friends", "Impulse"}

SYSTEM_INSTRUCTION = """You are SmartSpend AI, a smart, calm, and proactive AI financial assistant for college hostel and PG students in India.
You understand English, Indian English, Hindi, and Hinglish.
Your goal is to parse user intents, manage expenses, help students make wise spending decisions, and answer any financial questions about their data.
Always respond strictly in valid JSON matching the exact schema specified. Never output markdown code fences (do not wrap in ```json).

You are given:
1. Real-time Student Budget & Financial Context:
   - today_date: Current ISO date (YYYY-MM-DD)
   - active_categories: List of available categories in SQLite
   - monthly_budget: Monthly budget in ₹
   - total_spent_month: Total spent so far this month in ₹
   - spent_today: Total spent today in ₹
   - safe_to_spend_today: Calm daily allowance remaining for today in ₹
   - days_remaining: Days left in the month
   - category_totals: Spend breakdown by category { "Food": ..., "Travel": ... }
   - mood_totals: Spend breakdown by mood { "Essential": ..., "Craving": ..., "Friends": ..., "Impulse": ... }
   - pending_splits_total: Total ₹ owed back to user by friends from unsettled splits
   - cooldown_saved_total: Total ₹ saved from resisted impulse purchases in 48h Cooldown
   - recent_expenses: List of the last 10 expenses with id, date, amount, category, note, mood_tag, is_split, split_with

2. Recent Conversation History:
   Past exchanges between the user and assistant. Use this for multi-turn context (e.g. follow-ups, price clarifications).

ACTIONS YOU CAN TAKE (Choose strictly ONE):
1. "log_expense":
   When user specifies an expense with amount (e.g., "add 20 rs for food from Sharma shop", "50 rs for travel to college", "split 240 pizza with Raj and Amit", "yesterday 40 auto", or when user answers a prior clarification like "80"):
   - "action": "log_expense"
   - "transcript": Cleaned user message
   - "reply": Friendly, conversational confirmation mentioning category and safe balance remaining (e.g. "Logged ₹20 for Food (Sharma Shop). You have ₹280 safe to spend today.")
   - "expense": {
       "amount": float (total amount paid before split),
       "category": string (MUST be chosen from active_categories; default to closest or "Food"),
       "mood_tag": strictly one of ["Essential", "Craving", "Friends", "Impulse"],
       "split_count": integer >= 1 (e.g. "with Raj and Amit" = 3; "with 2 friends" = 3),
       "split_with": string with friend names if split, else "",
       "note": clean 2-4 word description of shop/place/item (e.g. "Food from Sharma Shop", "Travel to College", "Pizza with Raj, Amit", "Auto Fare", "Burger from Burger Mania"),
       "expense_date": ISO date YYYY-MM-DD (resolve "yesterday" as today_date - 1 day, else today_date)
     }

2. "clarify":
   CRITICAL: If the user mentions an item, place, or expense without an amount (e.g. "burger from Burger Mania", "chai with friends", "auto to station", "bought notebook"), DO NOT reset to a generic welcome greeting!
   - "action": "clarify"
   - "transcript": Cleaned user message
   - "reply": Natural, conversational question asking for the price (e.g. "Got it—Burger from Burger Mania! How much did it cost so I can log it for you?")
   - "expense": null

3. "delete_last_expense":
   When user asks to undo, delete, or remove their last expense (e.g. "delete my last expense", "remove that burger", "undo last spend"):
   - "action": "delete_last_expense"
   - "transcript": Cleaned user message
   - "reply": Confirmation that the last expense is being removed (e.g. "Removed your last expense.")
   - "expense": null

4. "add_cooldown":
   When user considers an impulse buy or wants to put an item into 48-hour cooldown (e.g. "I want to buy 1200 sneakers but put in cooldown", "put 800 headphones on hold", "cooling down 500 shirt"):
   - "action": "add_cooldown"
   - "transcript": Cleaned user message
   - "reply": Encouraging message noting the item is placed into the 48-hour cooling period to save money.
   - "cooldown_item": {
       "item_name": string (e.g. "Sneakers"),
       "amount": float (e.g. 1200.0)
     }

5. "advice":
   When user asks any question about their budget, status, analytics, affordability, or history (e.g. "How much did I spend on food today?", "What was my biggest expense this week?", "Can I afford a ₹150 burger right now?", "How much do my friends owe me?", "Can I treat myself tonight?"):
   - "action": "advice"
   - "transcript": Cleaned user message
   - "reply": Direct, insightful, empathetic 1-3 sentence answer referencing the exact numbers from the context.
   - "expense": null
"""


_CACHED_MODELS: Optional[List[str]] = None


def _get_candidate_models(client: Any) -> List[str]:
    """Query Google AI Studio for active models available to this API key or return ordered fallback."""
    global _CACHED_MODELS
    if _CACHED_MODELS:
        return _CACHED_MODELS

    default_candidates = [
        "gemini-3.5-flash-lite",
        "gemini-3.8-flash",
        "gemini-3.5-flash",
        "gemini-3.1-flash-lite",
        "gemini-3.6-flash",
        "gemini-1.5-flash",
        "gemini-2.5-flash",
    ]

    try:
        remote_models = []
        # Deprecated models known to return 404 for new users
        deprecated_models = {"gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash", "gemini-1.5-flash"}
        for m in client.models.list():
            raw_name = getattr(m, "name", "") or ""
            clean_name = raw_name.replace("models/", "").strip()
            if clean_name and any(kw in clean_name.lower() for kw in ["flash", "pro"]):
                if clean_name not in deprecated_models:
                    remote_models.append(clean_name)
        if remote_models:
            # Sort with preferred 3.x models first
            def _rank(name: str) -> int:
                if "3.5-flash-lite" in name:
                    return 0
                if "3.8-flash" in name:
                    return 1
                if "3.5-flash" in name:
                    return 2
                if "3.1-flash-lite" in name:
                    return 3
                if "flash" in name:
                    return 4
                return 5

            sorted_models = sorted(remote_models, key=_rank)
            _CACHED_MODELS = sorted_models
            print(f"[SmartSpend AI]: Discovered active models from Google AI Studio: {_CACHED_MODELS[:5]}")
            return _CACHED_MODELS
    except Exception as exc:
        print(f"[SmartSpend AI]: Note querying models.list(): {exc}")

    _CACHED_MODELS = default_candidates
    return _CACHED_MODELS


def check_ai_status() -> Dict[str, Any]:
    """Verify Gemini API configuration, connectivity status, and SDK installation."""
    load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env", override=True)
    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    sdk_installed = False
    try:
        from google import genai
        sdk_installed = True
    except ImportError:
        sdk_installed = False

    is_key_placeholder = api_key in ("your_google_ai_studio_key_here", "your_key_here")
    is_valid_key = bool(api_key and not is_key_placeholder)

    if not sdk_installed:
        error_hint = "google-genai SDK not installed in environment"
        status_label = "Fallback Mode"
        ai_mode = "fallback"
    elif not is_valid_key:
        error_hint = "Missing or unconfigured GEMINI_API_KEY in .env"
        status_label = "Fallback Mode"
        ai_mode = "fallback"
    else:
        error_hint = None
        status_label = "Gemini Connected"
        ai_mode = "gemini"

    model_name = _CACHED_MODELS[0] if _CACHED_MODELS else "gemini-3.8-flash"

    return {
        "gemini_configured": is_valid_key and sdk_installed,
        "sdk_installed": sdk_installed,
        "model": model_name,
        "status_label": status_label,
        "ai_mode": ai_mode,
        "error_hint": error_hint,
    }


def _get_genai_client() -> Tuple[Optional[Any], Optional[str]]:
    """Initialize and return the official google-genai Client, or (None, error_hint)."""
    status = check_ai_status()
    if not status["gemini_configured"]:
        return None, status["error_hint"]

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        return client, None
    except Exception as exc:
        err = f"google-genai client init error: {exc}"
        print(f"[SmartSpend AI Error]: {err}")
        return None, err


def _clean_gemini_json(text: str) -> str:
    """Extract and isolate JSON text from Gemini output, stripping code blocks or outer chatter."""
    clean = (text or "").strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", clean, re.DOTALL)
    if fence_match:
        return fence_match.group(1).strip()
    brace_match = re.search(r"(\{.*\})", clean, re.DOTALL)
    if brace_match:
        return brace_match.group(1).strip()
    return clean


def sanitize_note(raw_note: str, category: str) -> str:
    """Clean and prune raw text into a crisp 2-4 word memory anchor."""
    text = (raw_note or "").strip()
    text = re.sub(
        r"^(?:log|add|spent|paid|bought|track|record|please|i\s+spent)\s*(?:rs\.?|₹|\$)?\s*\d*(?:\.\d+)?\s*(?:for|on|in|at)?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s*(?:with|divided|split)\s*(?:by|with)?\s*\d*.*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^(?:for|on|in|at|to)\s+", "", text, flags=re.IGNORECASE).strip()

    words = text.split()
    if len(words) > 4:
        text = " ".join(words[:4])

    if not text or len(text) < 2:
        text = f"{category} spend"

    return text.title()[:40]


def _normalize_expense(
    data: Dict[str, Any],
    context: Dict[str, Any],
    today_iso: str,
) -> Optional[Dict[str, Any]]:
    """Validate and sanitize the expense dictionary from Gemini or fallback."""
    expense = data.get("expense")
    if not isinstance(expense, dict):
        return None

    try:
        amt = float(expense.get("amount", 0))
    except (ValueError, TypeError):
        return None

    if amt <= 0:
        return None

    allowed_cats = set(
        context.get("active_categories")
        or context.get("categories")
        or ["Food", "Travel", "Hostel/PG", "Fun", "Misc"]
    )
    cat = str(expense.get("category", "Food")).strip()
    if cat not in allowed_cats:
        cat = "Food" if "Food" in allowed_cats else next(iter(allowed_cats))

    mood = str(expense.get("mood_tag", "Essential")).strip()
    if mood not in ALLOWED_MOOD_TAGS:
        mood = "Essential"

    try:
        split_count = max(1, int(expense.get("split_count", 1)))
    except (ValueError, TypeError):
        split_count = 1

    split_with = str(expense.get("split_with", "")).strip()[:100]
    raw_note = str(expense.get("note", "")).strip()
    clean_note = sanitize_note(raw_note, cat)

    exp_date = str(expense.get("expense_date", today_iso)).strip()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", exp_date):
        exp_date = today_iso

    return {
        "amount": round(amt, 2),
        "category": cat,
        "mood_tag": mood,
        "split_count": split_count,
        "split_with": split_with,
        "note": clean_note,
        "expense_date": exp_date,
    }


def _offline_fallback(
    user_message: str,
    context: Dict[str, Any],
    history: Optional[List[Dict[str, str]]] = None,
    error_hint: Optional[str] = None,
) -> Dict[str, Any]:
    """Comprehensive local fallback engine handling multi-turn clarification, cooldowns, undo, and questions."""
    msg = user_message.lower().strip()
    today_iso = context.get("today_date") or datetime.date.today().strftime("%Y-%m-%d")
    safe_today = float(context.get("safe_to_spend_today", 0.0))
    spent_today = float(context.get("spent_today", 0.0))
    monthly_budget = float(context.get("monthly_budget", 3000.0))
    total_spent = float(context.get("total_spent_month", 0.0))
    pending_splits = float(context.get("pending_splits_total", 0.0))
    user_cats = context.get("active_categories") or context.get("categories") or ["Food", "Travel", "Hostel/PG", "Fun", "Misc"]
    recent_exps = context.get("recent_expenses") or []

    # 1. ACTION: Delete / Undo last expense
    if any(w in msg for w in ["delete last", "delete my last", "undo", "remove last", "cancel last", "remove expense"]):
        return {
            "action": "delete_last_expense",
            "intent": "delete_last_expense",
            "mode": "delete_last_expense",
            "transcript": user_message.strip(),
            "reply": "I'm removing your last logged expense now.",
            "expense": None,
            "cooldown_item": None,
            "ai_mode": "fallback",
            "error_hint": error_hint,
        }

    # 2. ACTION: Add 48h Cooldown Item
    if any(w in msg for w in ["cooldown", "cool down", "hold purchase", "impulse buy", "cooling down"]):
        amt_match = re.search(r"(?:rs\.?|₹|\$)?\s*(\d+(?:\.\d{1,2})?)", msg)
        amt = float(amt_match.group(1)) if amt_match else 500.0
        # Item name extraction with word boundaries so "sneakers" doesn't get clipped by "rs"
        cleaned_item = re.sub(
            r"\b(?:i\s+want\s+to\s+buy|buy|put|in\s+cooldown|cooling\s+down|for|rs|rupees|rupee)\b|[₹\$\d\.]+",
            "",
            msg,
            flags=re.IGNORECASE
        ).strip()
        item_name = cleaned_item.title() if cleaned_item else "Impulse Item"
        return {
            "action": "add_cooldown",
            "intent": "add_cooldown",
            "mode": "add_cooldown",
            "transcript": user_message.strip(),
            "reply": f"Added '{item_name}' (₹{amt:.0f}) to your 48-Hour Cooldown list. Take a breather and review it in 2 days!",
            "expense": None,
            "cooldown_item": {"item_name": item_name, "amount": amt},
            "ai_mode": "fallback",
            "error_hint": error_hint,
        }

    # 3. MULTI-TURN CLARIFICATION & AMOUNT DETECTION
    amount_match = re.search(r"(?:rs\.?|₹|\$)?\s*(\d+(?:\.\d{1,2})?)", msg)
    raw_amt = None
    if amount_match:
        raw_amt = float(amount_match.group(1))
    else:
        word_nums = {
            "ten": 10.0, "twenty": 20.0, "thirty": 30.0, "forty": 40.0, "fifty": 50.0,
            "sixty": 60.0, "seventy": 70.0, "eighty": 80.0, "ninety": 90.0, "hundred": 100.0,
            "two hundred": 200.0, "five hundred": 500.0, "bees": 20.0, "tees": 30.0,
            "chaalis": 40.0, "pachaas": 50.0, "sau": 100.0, "do sau": 200.0
        }
        for wn, val in word_nums.items():
            if wn in msg:
                raw_amt = val
                break

    # If user provided ONLY an amount (or very short e.g. "80", "₹80", "it was 80") and prior assistant asked for price:
    if raw_amt is not None and len(msg.split()) <= 4 and history:
        last_assistant = next((h["text"] for h in reversed(history) if h.get("role") == "assistant"), "")
        clarify_match = re.search(r"Got it—(.*?)[!.]", last_assistant)
        if clarify_match:
            prior_item = clarify_match.group(1).strip()
            my_share = raw_amt
            reply = f"Logged ₹{my_share:.2f} for Food ({prior_item}). Safe to spend today is now ₹{max(0.0, safe_today - my_share):.2f}."
            return {
                "action": "log_expense",
                "intent": "log_expense",
                "mode": "log_expense",
                "transcript": user_message.strip(),
                "reply": reply,
                "expense": {
                    "amount": raw_amt,
                    "category": "Food",
                    "mood_tag": "Craving",
                    "split_count": 1,
                    "split_with": "",
                    "note": prior_item,
                    "expense_date": today_iso,
                },
                "cooldown_item": None,
                "ai_mode": "fallback",
                "error_hint": error_hint,
            }

    # If user mentioned an item or shop WITHOUT an amount (e.g. "burger from Burger Mania", "chai with friends", "auto to college"):
    item_keywords = ["burger", "pizza", "chai", "coffee", "biryani", "dosa", "sandwich", "tiffin", "auto", "cab", "metro", "recharge", "notebook", "printout"]
    has_item = any(ik in msg for ik in item_keywords) or any(shop in msg for shop in ["mania", "sharma", "canteen", "cafe", "dhaba", "mess"])
    if raw_amt is None and has_item:
        clean_item = sanitize_note(user_message, "Food")
        return {
            "action": "clarify",
            "intent": "clarify",
            "mode": "clarify",
            "transcript": user_message.strip(),
            "reply": f"Got it—{clean_item}! How much did it cost so I can log it for you?",
            "expense": None,
            "cooldown_item": None,
            "ai_mode": "fallback",
            "error_hint": error_hint,
        }

    # 4. ACTION: Specific Context Questions & Affordability (takes precedence if question phrases detected)
    is_question = any(w in msg for w in ["can i", "afford", "how much", "what was", "should i", "status", "owe"])
    if is_question:
        if any(w in msg for w in ["food today", "spend on food today", "spent on food"]):
            food_today = sum(e["amount"] for e in recent_exps if e.get("category") == "Food" and e.get("date") == today_iso)
            cat_food = context.get("category_totals", {}).get("Food", 0.0)
            return {
                "action": "advice",
                "intent": "advice",
                "mode": "advice",
                "transcript": user_message.strip(),
                "reply": f"You've spent ₹{food_today:.2f} on Food today (and ₹{cat_food:.2f} total on Food this month).",
                "expense": None,
                "cooldown_item": None,
                "ai_mode": "fallback",
                "error_hint": error_hint,
            }

        if any(w in msg for w in ["biggest", "highest", "most expensive"]):
            if recent_exps:
                biggest = max(recent_exps, key=lambda x: x.get("amount", 0))
                return {
                    "action": "advice",
                    "intent": "advice",
                    "mode": "advice",
                    "transcript": user_message.strip(),
                    "reply": f"Your biggest recent expense was ₹{biggest['amount']:.2f} for '{biggest.get('note', 'Expense')}' on {biggest.get('date', 'recently')}.",
                    "expense": None,
                    "cooldown_item": None,
                    "ai_mode": "fallback",
                    "error_hint": error_hint,
                }

        if any(w in msg for w in ["owe", "friends owe", "pending splits"]):
            return {
                "action": "advice",
                "intent": "advice",
                "mode": "advice",
                "transcript": user_message.strip(),
                "reply": f"Your roommates and friends owe you ₹{pending_splits:.2f} across pending unsettled splits.",
                "expense": None,
                "cooldown_item": None,
                "ai_mode": "fallback",
                "error_hint": error_hint,
            }

        if any(w in msg for w in ["afford", "can i", "budget", "safe", "left", "treat"]):
            if raw_amt is not None:
                if raw_amt <= safe_today:
                    reply = f"Yes! ₹{raw_amt:.0f} fits within your ₹{safe_today:.2f} safe daily limit. Enjoy it peacefully!"
                else:
                    excess = raw_amt - safe_today
                    reply = f"A ₹{raw_amt:.0f} spend would put you ₹{excess:.0f} over today's ₹{safe_today:.2f} safe limit. Consider cooling down or waiting for tomorrow!"
            elif safe_today > 100:
                reply = f"You have ₹{safe_today:.2f} safe to spend today (₹{total_spent:.0f} of ₹{monthly_budget:.0f} used). A modest treat fits comfortably within your daily limit."
            elif safe_today > 0:
                reply = f"Your safe daily allowance is ₹{safe_today:.2f}. Keeping spends light today will help you finish the month peacefully."
            else:
                reply = f"Today's calm limit is at ₹0 after recent spends (₹{total_spent:.0f} used this month). Sticking to mess essentials today will quickly bring your allowance back on track."
            return {
                "action": "advice",
                "intent": "advice",
                "mode": "advice",
                "transcript": user_message.strip(),
                "reply": reply,
                "expense": None,
                "cooldown_item": None,
                "ai_mode": "fallback",
                "error_hint": error_hint,
            }

    # 5. ACTION: Direct Expense Logging
    keywords = [
        "spent", "bought", "paid", "chai", "auto", "tiffin", "snack", "biryani",
        "recharge", "coffee", "food", "travel", "cab", "lunch", "dinner", "pizza",
        "sharma", "college", "add", "log", "yesterday", "rickshaw", "metro", "bus",
        "kharcha", "rupaye", "rupees", "rupee", "rs", "mess", "canteen", "samosa",
        "maggi", "maggie", "juice", "stationary", "print", "xerox", "roommate", "dost"
    ]

    if raw_amt is not None and (amount_match or any(kw in msg for kw in keywords)):
        # Calculate date
        expense_date = today_iso
        try:
            base_d = datetime.date.fromisoformat(today_iso)
            if "yesterday" in msg:
                expense_date = (base_d - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
            elif "day before yesterday" in msg:
                expense_date = (base_d - datetime.timedelta(days=2)).strftime("%Y-%m-%d")
        except Exception:
            expense_date = today_iso

        # Split check
        split_count = 1
        split_with = ""
        named_split = re.search(r"with\s+([a-zA-Z\s,&]+)", msg)
        if named_split and not re.search(r"\d+\s*friends?", named_split.group(1)):
            names_raw = named_split.group(1).replace("and", ",").replace("&", ",")
            names_list = [n.strip().title() for n in names_raw.split(",") if n.strip() and n.strip().lower() not in ["me", "i"]]
            if names_list:
                split_count = len(names_list) + 1
                split_with = ", ".join(names_list)

        if split_count == 1:
            split_by = re.search(r"(?:split|divided)\s*(?:by)?\s*(\d+)", msg)
            friends_num = re.search(r"(?:with)\s*(\d+)\s*friends?", msg)
            if split_by:
                split_count = max(1, int(split_by.group(1)))
            elif friends_num:
                split_count = max(1, int(friends_num.group(1)) + 1)
                split_with = f"{friends_num.group(1)} friends"

        # Category
        category = "Food" if "Food" in user_cats else user_cats[0]
        matched_cat = False
        for uc in user_cats:
            if uc.lower() in msg:
                category = uc
                matched_cat = True
                break
        if not matched_cat:
            if any(w in msg for w in ["auto", "cab", "uber", "ola", "bus", "metro", "petrol", "travel", "rickshaw"]) and "Travel" in user_cats:
                category = "Travel"
            elif any(w in msg for w in ["rent", "pg", "hostel", "room", "mess fee"]) and "Hostel/PG" in user_cats:
                category = "Hostel/PG"
            elif any(w in msg for w in ["movie", "game", "gaming", "outing", "party", "fun"]) and "Fun" in user_cats:
                category = "Fun"
            elif any(w in msg for w in ["stationary", "print", "xerox", "book", "misc"]) and "Misc" in user_cats:
                category = "Misc"

        mood = "Essential"
        if split_count > 1 or any(w in msg for w in ["friends", "friend", "roommate", "group", "treat", "party"]):
            mood = "Friends"
        elif any(w in msg for w in ["craving", "crave", "chips", "maggi", "midnight", "sweet", "pizza", "burger"]):
            mood = "Craving"
        elif any(w in msg for w in ["impulse", "unplanned", "sale", "online", "amazon"]):
            mood = "Impulse"

        note = sanitize_note(user_message, category)
        if "sharma" in msg:
            note = "Food from Sharma Shop"
        elif "college" in msg or "collage" in msg:
            note = "Travel to College"
        elif "pizza" in msg:
            note = f"Pizza with {split_with}" if split_with else "Pizza"
        elif "auto" in msg:
            note = "Auto Fare"
        elif "burger" in msg and "mania" in msg:
            note = "Burger from Burger Mania"

        my_share = round(raw_amt / split_count, 2)
        if split_count > 1:
            reply = f"Split ₹{raw_amt:.0f} {split_count} ways ({split_with or 'friends'}): your share is ₹{my_share:.2f}. Safe today is ₹{max(0.0, safe_today - my_share):.2f}."
        else:
            reply = f"Logged ₹{my_share:.2f} ({category} • {mood}) as '{note}'. Safe today is ₹{max(0.0, safe_today - my_share):.2f}."

        return {
            "action": "log_expense",
            "intent": "log_expense",
            "mode": "log_expense",
            "transcript": user_message.strip(),
            "reply": reply,
            "expense": {
                "amount": raw_amt,
                "category": category,
                "mood_tag": mood,
                "split_count": split_count,
                "split_with": split_with,
                "note": note,
                "expense_date": expense_date,
            },
            "cooldown_item": None,
            "ai_mode": "fallback",
            "error_hint": error_hint,
        }

    # 5. ACTION: Specific Context Questions
    if any(w in msg for w in ["food today", "spend on food today", "spent on food"]):
        food_today = sum(e["amount"] for e in recent_exps if e.get("category") == "Food" and e.get("date") == today_iso)
        cat_food = context.get("category_totals", {}).get("Food", 0.0)
        return {
            "action": "advice",
            "intent": "advice",
            "mode": "advice",
            "transcript": user_message.strip(),
            "reply": f"You've spent ₹{food_today:.2f} on Food today (and ₹{cat_food:.2f} total on Food this month).",
            "expense": None,
            "cooldown_item": None,
            "ai_mode": "fallback",
            "error_hint": error_hint,
        }

    if any(w in msg for w in ["biggest", "highest", "most expensive"]):
        if recent_exps:
            biggest = max(recent_exps, key=lambda x: x.get("amount", 0))
            return {
                "action": "advice",
                "intent": "advice",
                "mode": "advice",
                "transcript": user_message.strip(),
                "reply": f"Your biggest recent expense was ₹{biggest['amount']:.2f} for '{biggest.get('note', 'Expense')}' on {biggest.get('date', 'recently')}.",
                "expense": None,
                "cooldown_item": None,
                "ai_mode": "fallback",
                "error_hint": error_hint,
            }

    if any(w in msg for w in ["owe", "friends owe", "pending splits"]):
        return {
            "action": "advice",
            "intent": "advice",
            "mode": "advice",
            "transcript": user_message.strip(),
            "reply": f"Your roommates and friends owe you ₹{pending_splits:.2f} across pending unsettled splits.",
            "expense": None,
            "cooldown_item": None,
            "ai_mode": "fallback",
            "error_hint": error_hint,
        }

    if any(w in msg for w in ["afford", "can i", "budget", "safe", "left", "how much", "status", "treat"]):
        if safe_today > 100:
            reply = f"You have ₹{safe_today:.2f} safe to spend today (₹{total_spent:.0f} of ₹{monthly_budget:.0f} used). A modest treat fits comfortably within your daily limit."
        elif safe_today > 0:
            reply = f"Your safe daily allowance is ₹{safe_today:.2f}. Keeping spends light today will help you finish the month peacefully."
        else:
            reply = f"Today's calm limit is at ₹0 after recent spends (₹{total_spent:.0f} used this month). Sticking to mess essentials today will quickly bring your allowance back on track."
        return {
            "action": "advice",
            "intent": "advice",
            "mode": "advice",
            "transcript": user_message.strip(),
            "reply": reply,
            "expense": None,
            "cooldown_item": None,
            "ai_mode": "fallback",
            "error_hint": error_hint,
        }

    return {
        "action": "advice",
        "intent": "advice",
        "mode": "advice",
        "transcript": user_message.strip(),
        "reply": f"SmartSpend AI here! You have ₹{safe_today:.2f} safe to spend today out of your ₹{monthly_budget:.0f} monthly budget. Tell me what you spent or ask for advice!",
        "expense": None,
        "cooldown_item": None,
        "ai_mode": "fallback",
        "error_hint": error_hint,
    }


def process_ai_text(
    user_message: str,
    context: Dict[str, Any],
    history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Process natural language text command with Gemini 2.5 Flash, multi-turn history, and auto-retry."""
    clean_msg = (user_message or "").strip()
    today_iso = context.get("today_date") or datetime.date.today().strftime("%Y-%m-%d")

    if not clean_msg:
        return {
            "action": "advice",
            "intent": "advice",
            "mode": "advice",
            "transcript": "",
            "reply": "How can I help with your budget today? Tell me what you spent or ask for advice!",
            "expense": None,
            "cooldown_item": None,
            "ai_mode": "fallback",
            "error_hint": None,
        }

    client, error_hint = _get_genai_client()
    if not client:
        return _offline_fallback(clean_msg, context, history, error_hint=error_hint)

    # Format multi-turn conversation history
    history_lines = []
    if history:
        for h in history[-8:]:
            role = "User" if h.get("role") == "user" else "SmartSpend AI"
            history_lines.append(f"{role}: {h.get('text', '')}")
    history_str = "\n".join(history_lines) if history_lines else "None (New conversation)"

    recent_exps_str = json.dumps(context.get("recent_expenses", []), indent=2)

    prompt = f"""Student Budget & Financial Context:
- today_date: "{today_iso}"
- active_categories: {json.dumps(context.get('active_categories', ['Food', 'Travel', 'Hostel/PG', 'Fun', 'Misc']))}
- monthly_budget: ₹{context.get('monthly_budget', 3000.0)}
- total_spent_month: ₹{context.get('total_spent_month', 0.0)}
- spent_today: ₹{context.get('spent_today', 0.0)}
- safe_to_spend_today: ₹{context.get('safe_to_spend_today', 0.0)}
- days_remaining: {context.get('days_remaining', 10)}
- category_totals: {json.dumps(context.get('category_totals', {}))}
- mood_totals: {json.dumps(context.get('mood_totals', {}))}
- pending_splits_total: ₹{context.get('pending_splits_total', 0.0)}
- cooldown_saved_total: ₹{context.get('cooldown_saved_total', 0.0)}
- recent_expenses (last 10): {recent_exps_str}

Recent Conversation History:
{history_str}

User Message: "{clean_msg}"
"""

    models_to_try = _get_candidate_models(client)
    last_err = None

    try:
        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            temperature=0.3,
        )

        response_text = None
        used_model = None

        for m in models_to_try:
            try:
                resp = client.models.generate_content(
                    model=m,
                    contents=prompt,
                    config=config,
                )
                response_text = resp.text
                used_model = m
                print(f"[SmartSpend AI Success]: Model '{used_model}' generated response successfully.")
                break
            except Exception as exc:
                last_err = exc
                print(f"[SmartSpend AI Error]: Model {m} failed: {repr(exc)}")
                continue

        if not response_text:
            raise last_err or RuntimeError("All Gemini models failed")

        cleaned_json = _clean_gemini_json(response_text)
        data = json.loads(cleaned_json)

        action = data.get("action") or data.get("intent") or data.get("mode") or "advice"
        transcript = data.get("transcript") or clean_msg
        reply = data.get("reply", "Here is your spending update.")
        expense = _normalize_expense(data, context, today_iso)
        cooldown_item = data.get("cooldown_item")

        if action == "log_expense" and not expense:
            action = "clarify" if "how much" in reply.lower() else "advice"

        return {
            "action": action,
            "intent": action,
            "mode": action,
            "transcript": transcript,
            "reply": reply,
            "expense": expense,
            "cooldown_item": cooldown_item,
            "ai_mode": "gemini",
            "model": used_model,
            "error_hint": None,
        }

    except Exception as exc:
        print(f"[SmartSpend AI Error]: {repr(exc)}")
        return _offline_fallback(clean_msg, context, history, error_hint=str(exc))


def process_ai_audio(
    audio_bytes: bytes,
    mime_type: str,
    context: Dict[str, Any],
    history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Process multimodal audio speech directly with Gemini 2.5 Flash, multi-turn history, and auto-retry."""
    today_iso = context.get("today_date") or datetime.date.today().strftime("%Y-%m-%d")

    # Sanitize and normalize audio MIME type for Gemini API
    if mime_type:
        mime_type = mime_type.split(";")[0].strip().lower()
    if mime_type not in ["audio/webm", "audio/wav", "audio/mp3", "audio/mpeg", "audio/ogg", "audio/aac", "audio/flac"]:
        mime_type = "audio/webm"

    client, error_hint = _get_genai_client()
    if not client:
        return {
            "action": "advice",
            "intent": "advice",
            "mode": "advice",
            "transcript": "Audio command received",
            "reply": "Google AI Studio is offline or unconfigured. You can type commands directly into SmartSpend AI!",
            "expense": None,
            "cooldown_item": None,
            "ai_mode": "fallback",
            "error_hint": error_hint,
        }

    history_lines = []
    if history:
        for h in history[-8:]:
            role = "User" if h.get("role") == "user" else "SmartSpend AI"
            history_lines.append(f"{role}: {h.get('text', '')}")
    history_str = "\n".join(history_lines) if history_lines else "None (New conversation)"

    recent_exps_str = json.dumps(context.get("recent_expenses", []), indent=2)

    prompt_instruction = f"""Listen carefully to the student's speech in English, Hindi, or Hinglish.
Transcribe what they said into 'transcript', decide the appropriate action ("log_expense", "clarify", "delete_last_expense", "add_cooldown", or "advice"), and output strictly in JSON.

Student Budget & Financial Context:
- today_date: "{today_iso}"
- active_categories: {json.dumps(context.get('active_categories', ['Food', 'Travel', 'Hostel/PG', 'Fun', 'Misc']))}
- monthly_budget: ₹{context.get('monthly_budget', 3000.0)}
- total_spent_month: ₹{context.get('total_spent_month', 0.0)}
- spent_today: ₹{context.get('spent_today', 0.0)}
- safe_to_spend_today: ₹{context.get('safe_to_spend_today', 0.0)}
- days_remaining: {context.get('days_remaining', 10)}
- category_totals: {json.dumps(context.get('category_totals', {}))}
- mood_totals: {json.dumps(context.get('mood_totals', {}))}
- pending_splits_total: ₹{context.get('pending_splits_total', 0.0)}
- cooldown_saved_total: ₹{context.get('cooldown_saved_total', 0.0)}
- recent_expenses (last 10): {recent_exps_str}

Recent Conversation History:
{history_str}
"""

    models_to_try = _get_candidate_models(client)
    last_err = None

    try:
        from google.genai import types

        audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            temperature=0.3,
        )

        response_text = None
        used_model = None

        for m in models_to_try:
            try:
                resp = client.models.generate_content(
                    model=m,
                    contents=[prompt_instruction, audio_part],
                    config=config,
                )
                response_text = resp.text
                used_model = m
                print(f"[SmartSpend AI Success]: Model '{used_model}' processed audio successfully.")
                break
            except Exception as exc:
                last_err = exc
                print(f"[SmartSpend AI Error]: Model {m} audio failed: {repr(exc)}")
                continue

        if not response_text:
            raise last_err or RuntimeError("All Gemini audio models failed")

        cleaned_json = _clean_gemini_json(response_text)
        data = json.loads(cleaned_json)

        action = data.get("action") or data.get("intent") or data.get("mode") or "advice"
        transcript = data.get("transcript") or "Voice command"
        reply = data.get("reply", "Voice command processed.")
        expense = _normalize_expense(data, context, today_iso)
        cooldown_item = data.get("cooldown_item")

        if action == "log_expense" and not expense:
            action = "clarify" if "how much" in reply.lower() else "advice"

        return {
            "action": action,
            "intent": action,
            "mode": action,
            "transcript": transcript,
            "reply": reply,
            "expense": expense,
            "cooldown_item": cooldown_item,
            "ai_mode": "gemini",
            "model": used_model,
            "error_hint": None,
        }

    except Exception as exc:
        print(f"[SmartSpend AI Error]: {repr(exc)}")
        return {
            "action": "advice",
            "intent": "advice",
            "mode": "advice",
            "transcript": "Voice command",
            "reply": f"Could not process voice audio via Google AI Studio ({str(exc)[:60]}). You can type your command directly!",
            "expense": None,
            "cooldown_item": None,
            "ai_mode": "fallback",
            "error_hint": str(exc),
        }


def handle_ai_chat(user_message: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Backwards-compatible wrapper calling process_ai_text."""
    return process_ai_text(user_message, context)
