"""app.py - Main Flask Web Application and REST API Suite for SmartSpend.

Page Routes:
- /               (Overview Dashboard: Hero, Quick Log, Snapshot, Recent 5)
- /log-expense    (Fast 5-Sec Logger: Rapid amounts, Presets, Custom Categories, Split)
- /transactions   (Full Ledger: Live search, Date/Category/Intent filters, Edit, 5-Sec Undo)
- /calendar       (Monthly Spending Calendar: Day totals, Daily Target, Mood checks)
- /splits-bills   (Hostel Management: Owed splits tracking, Settle button, Recurring Monthly Bills)
- /cooldown       (48-Hour Impulse Holding Tank with Live Countdowns)

REST APIs:
- /api/session, /api/dashboard, /api/expenses (GET/POST/PUT/DELETE/RESTORE/SETTLE)
- /api/splits-bills, /api/recurring (GET/POST/DELETE/LOG)
- /api/insights, /api/cooldown, /api/ai-chat, /api/export/<type>
"""

import csv
import datetime
import io
import os
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

# Explicitly load .env relative to the spendcalm project directory
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env", override=True)

from flask import (
    Flask,
    Response,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

import ai_helper
import models

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.getenv("FLASK_SECRET_KEY", "spendcalm_default_dev_secret_key_change_me")

# Ensure database tables and non-destructive migrations exist at startup
models.init_db()


def get_current_user() -> Dict[str, Any]:
    """Retrieve active session participant, auto-initializing P01 default if none."""
    user_id = session.get("user_id")
    if user_id:
        user = models.get_user_by_id(user_id)
        if user:
            return user

    user = models.get_or_create_user("P01", 3000.0)
    session["user_id"] = user["id"]
    session["participant_code"] = user["participant_code"]
    return user


# -------------------------------------------------------------------------
# Page Routes (HTML Views)
# -------------------------------------------------------------------------

@app.route("/")
def index():
    """Render the Calm Overview Dashboard (Hero, Quick Log, Snapshot, Recent 5)."""
    user = get_current_user()
    pending_count = len(models.get_unsettled_splits(user["id"]))
    return render_template("index.html", user=user, active_page="dashboard", pending_splits_count=pending_count)


@app.route("/transactions")
def transactions():
    """Render the Full Transaction Ledger view."""
    user = get_current_user()
    pending_count = len(models.get_unsettled_splits(user["id"]))
    return render_template("transactions.html", user=user, active_page="transactions", pending_splits_count=pending_count)


@app.route("/calendar")
def calendar_view():
    """Render the Monthly Spending Calendar view."""
    user = get_current_user()
    pending_count = len(models.get_unsettled_splits(user["id"]))
    return render_template("calendar.html", user=user, active_page="calendar", pending_splits_count=pending_count)


@app.route("/log-expense")
def log_expense():
    """Render dedicated Rapid Expense Logger view."""
    user = get_current_user()
    pending_count = len(models.get_unsettled_splits(user["id"]))
    return render_template("log_expense.html", user=user, active_page="log_expense", pending_splits_count=pending_count)


@app.route("/insights")
def insights():
    """Redirect cleanly (302) to Insights section on Overview dashboard."""
    return redirect("/#insights-section", code=302)


@app.route("/splits-bills")
def splits_bills():
    """Render the Hostel Splits & Recurring Bills Management view."""
    user = get_current_user()
    pending_count = len(models.get_unsettled_splits(user["id"]))
    return render_template("splits_bills.html", user=user, active_page="splits_bills", pending_splits_count=pending_count)


@app.route("/cooldown")
def cooldown():
    """Render the 48-Hour Impulse Cooldown wishlist."""
    user = get_current_user()
    pending_count = len(models.get_unsettled_splits(user["id"]))
    return render_template("cooldown.html", user=user, active_page="cooldown", pending_splits_count=pending_count)


@app.route("/test-mode")
def test_mode():
    """Redirect legacy usability test-mode route to overview."""
    return redirect("/", code=302)


@app.route("/feedback")
def feedback():
    """Redirect legacy feedback route to overview."""
    return redirect("/", code=302)


# -------------------------------------------------------------------------
# REST API Endpoints
# -------------------------------------------------------------------------

@app.route("/api/session", methods=["GET", "POST"])
def api_session():
    """Get active session or set/switch participant code and budget."""
    if request.method == "GET":
        user = get_current_user()
        return jsonify({"status": "ok", "user": user})

    data = request.get_json(silent=True) or {}
    code = str(data.get("participant_code", "")).strip().upper()
    if not code:
        code = session.get("participant_code", "P01")

    try:
        budget = float(data.get("monthly_budget", 3000.0))
        if budget <= 0 or budget > 100000:
            return jsonify({"error": "Budget must be between ₹100 and ₹1,00,000."}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid budget value."}), 400

    user = models.get_or_create_user(code, budget)
    if "monthly_budget" in data:
        models.update_user_budget(user["id"], budget)
        user["monthly_budget"] = budget

    session["user_id"] = user["id"]
    session["participant_code"] = user["participant_code"]

    return jsonify({"status": "ok", "user": user})


@app.route("/api/dashboard", methods=["GET"])
def api_dashboard():
    """Fetch complete dashboard state for the Overview screen."""
    user = get_current_user()
    dashboard_data = models.calculate_safe_to_spend(user["id"])
    recent_expenses = models.get_expenses(user["id"], limit=5)
    pending_splits_total = models.get_pending_splits_total(user["id"])
    pending_splits_count = len(models.get_unsettled_splits(user["id"]))
    cooldown_saved_total = models.get_total_cooldown_saved(user["id"])

    return jsonify({
        "status": "ok",
        "user": user,
        "metrics": dashboard_data,
        "recent_expenses": recent_expenses,
        "expenses": recent_expenses,
        "pending_splits_total": pending_splits_total,
        "pending_splits_count": pending_splits_count,
        "cooldown_saved_total": cooldown_saved_total,
    })


@app.route("/api/expenses", methods=["GET", "POST"])
def api_expenses():
    """Fetch expenses with filters or rapidly log a new expense."""
    user = get_current_user()

    if request.method == "GET":
        cat = request.args.get("category")
        mood = request.args.get("mood_tag")
        search = request.args.get("search")
        date_range = request.args.get("range", "all")
        limit = int(request.args.get("limit", 100))

        expenses = models.get_expenses(
            user["id"],
            category=cat,
            mood_tag=mood,
            search=search,
            date_range=date_range,
            limit=limit,
        )
        return jsonify({"status": "ok", "expenses": expenses})

    data = request.get_json(silent=True) or {}
    try:
        raw_amt = float(data.get("amount", 0))
        if raw_amt <= 0:
            return jsonify({"error": "Expense amount must be greater than zero."}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid expense amount."}), 400

    category = data.get("category", "Food")
    mood_tag = data.get("mood_tag", "Essential")
    is_split = bool(data.get("is_split", False))
    split_count = int(data.get("split_count", 1)) if is_split else 1
    split_with = str(data.get("split_with", "")).strip()[:100]
    note = str(data.get("note", "")).strip()[:60]
    expense_date = str(data.get("expense_date", "")).strip() or None

    try:
        expense_id = models.add_expense(
            user_id=user["id"],
            amount=raw_amt,
            category=category,
            mood_tag=mood_tag,
            is_split=is_split,
            split_count=split_count,
            split_with=split_with,
            note=note,
            expense_date=expense_date,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    logged_amount = round(raw_amt / split_count, 2) if is_split and split_count > 1 else raw_amt
    metrics = models.calculate_safe_to_spend(user["id"])

    return jsonify({
        "status": "created",
        "expense_id": expense_id,
        "logged_amount": logged_amount,
        "metrics": metrics,
    }), 201


@app.route("/api/expenses/<int:expense_id>", methods=["PUT", "DELETE"])
def api_single_expense(expense_id: int):
    """Edit an existing expense or delete with 5-second undo backup."""
    user = get_current_user()

    if request.method == "DELETE":
        deleted = models.delete_expense(expense_id, user_id=user["id"])
        if not deleted:
            return jsonify({"error": "Expense not found or unauthorized."}), 404
        metrics = models.calculate_safe_to_spend(user["id"])
        return jsonify({"status": "deleted", "id": expense_id, "metrics": metrics})

    # PUT: Edit Expense
    data = request.get_json(silent=True) or {}
    try:
        raw_amt = float(data.get("amount", 0))
        if raw_amt <= 0:
            return jsonify({"error": "Expense amount must be greater than zero."}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid expense amount."}), 400

    category = data.get("category", "Food")
    mood_tag = data.get("mood_tag", "Essential")
    note = str(data.get("note", "")).strip()[:60]
    expense_date = str(data.get("expense_date", "")).strip() or None
    is_split = bool(data.get("is_split", False))
    split_count = int(data.get("split_count", 1)) if is_split else 1
    split_with = str(data.get("split_with", "")).strip()[:100]

    try:
        updated = models.update_expense(
            expense_id=expense_id,
            user_id=user["id"],
            amount=raw_amt,
            category=category,
            mood_tag=mood_tag,
            note=note,
            expense_date=expense_date,
            is_split=is_split,
            split_count=split_count,
            split_with=split_with,
        )
        if not updated:
            return jsonify({"error": "Expense not found or unauthorized."}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    metrics = models.calculate_safe_to_spend(user["id"])
    return jsonify({"status": "updated", "id": expense_id, "metrics": metrics})


@app.route("/api/expenses/restore", methods=["POST"])
def api_restore_expense():
    """5-Second Undo: Restore a deleted expense back into active ledger."""
    user = get_current_user()
    data = request.get_json(silent=True) or {}
    expense_id = data.get("expense_id")
    if not expense_id:
        return jsonify({"error": "expense_id required"}), 400

    success = models.restore_expense(int(expense_id), user["id"])
    if not success:
        return jsonify({"error": "Expense could not be restored."}), 404

    metrics = models.calculate_safe_to_spend(user["id"])
    return jsonify({"status": "restored", "id": expense_id, "metrics": metrics})


# -------------------------------------------------------------------------
# Category CRUD REST APIs
# -------------------------------------------------------------------------

@app.route("/api/categories", methods=["GET", "POST"])
def api_categories():
    """Retrieve all categories for the active user or create a new custom category."""
    user = get_current_user()

    if request.method == "GET":
        cats = models.get_categories(user["id"])
        return jsonify({"status": "ok", "categories": cats})

    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    icon = str(data.get("icon", "tag")).strip()
    color = str(data.get("color", "#6B7280")).strip()

    try:
        new_cat = models.add_category(user["id"], name, icon, color)
        return jsonify({"status": "created", "category": new_cat}), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/categories/<int:cat_id>", methods=["PUT", "DELETE"])
def api_single_category(cat_id: int):
    """Update or delete a custom category."""
    user = get_current_user()

    if request.method == "DELETE":
        try:
            success = models.delete_category(cat_id, user["id"])
            if not success:
                return jsonify({"error": "Category not found or unauthorized."}), 404
            return jsonify({"status": "deleted", "id": cat_id})
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    # PUT: Update / Rename Category
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    icon = str(data.get("icon", "tag")).strip()
    color = str(data.get("color", "#6B7280")).strip()

    try:
        updated_cat = models.update_category(cat_id, user["id"], name, icon, color)
        return jsonify({"status": "updated", "category": updated_cat})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/expenses/<int:expense_id>/settle", methods=["POST"])
def api_settle_split(expense_id: int):
    """Mark a pending friend split as settled."""
    user = get_current_user()
    success = models.settle_split(expense_id, user["id"])
    if not success:
        return jsonify({"error": "Split expense not found or already settled."}), 404

    pending_total = models.get_pending_splits_total(user["id"])
    return jsonify({"status": "settled", "id": expense_id, "pending_total": pending_total})


@app.route("/api/splits-bills", methods=["GET"])
def api_splits_bills():
    """Retrieve all pending splits, settled splits, and recurring bill templates."""
    user = get_current_user()
    pending_splits = models.get_unsettled_splits(user["id"])
    settled_splits = models.get_settled_splits(user["id"])
    pending_total = models.get_pending_splits_total(user["id"])
    recurring = models.get_recurring_bills(user["id"])

    return jsonify({
        "status": "ok",
        "pending_total": pending_total,
        "pending_splits": pending_splits,
        "settled_splits": settled_splits,
        "recurring_bills": recurring,
    })


@app.route("/api/recurring", methods=["GET", "POST"])
def api_recurring_bills():
    """Manage fixed monthly bills (PG rent, mess fee, Wi-Fi, etc.)."""
    user = get_current_user()

    if request.method == "GET":
        bills = models.get_recurring_bills(user["id"])
        return jsonify({"status": "ok", "bills": bills})

    data = request.get_json(silent=True) or {}
    title = str(data.get("title", "")).strip()
    try:
        amt = float(data.get("amount", 0))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid amount"}), 400

    category = data.get("category", "Hostel/PG")
    try:
        bill = models.add_recurring_bill(user["id"], title, amt, category)
        return jsonify({"status": "created", "bill": bill}), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/recurring/<int:bill_id>", methods=["DELETE"])
def api_delete_recurring(bill_id: int):
    """Delete a recurring bill template."""
    user = get_current_user()
    deleted = models.delete_recurring_bill(bill_id, user["id"])
    if not deleted:
        return jsonify({"error": "Bill not found."}), 404
    return jsonify({"status": "deleted", "id": bill_id})


@app.route("/api/recurring/<int:bill_id>/log", methods=["POST"])
def api_log_recurring(bill_id: int):
    """1-Tap log a recurring bill for the current month into expenses."""
    user = get_current_user()
    current_month_str = datetime.date.today().strftime("%Y-%m")
    try:
        res = models.log_recurring_bill(bill_id, user["id"], current_month_str)
        metrics = models.calculate_safe_to_spend(user["id"])
        res["metrics"] = metrics
        return jsonify(res), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404


@app.route("/api/insights", methods=["GET"])
def api_insights():
    """Fetch analytics for the /insights page."""
    user = get_current_user()
    data = models.get_insights_data(user["id"])
    return jsonify({
        "status": "ok",
        **data,
        "insights": data
    })


@app.route("/api/calendar", methods=["GET"])
def api_calendar():
    """Return month-by-month calendar spending summary and daily breakdown."""
    user = get_current_user()
    today = datetime.date.today()
    try:
        year = int(request.args.get("year", today.year))
        month = int(request.args.get("month", today.month))
        if month < 1 or month > 12:
            return jsonify({"error": "Month must be between 1 and 12."}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid year or month parameter."}), 400

    data = models.get_monthly_calendar_data(user["id"], year, month)
    return jsonify(data)


@app.route("/api/mood-checkin", methods=["POST"])
def api_mood_checkin():
    """Log or update wallet mood check-in for a specific calendar date."""
    user = get_current_user()
    data = request.get_json(silent=True) or {}
    checkin_date = data.get("date")
    mood = data.get("mood", "").strip()
    if not checkin_date or not mood:
        return jsonify({"error": "Date and mood are required."}), 400
    try:
        res = models.log_mood_checkin(user["id"], checkin_date, mood)
        return jsonify(res)
    except Exception as err:
        return jsonify({"error": str(err)}), 400


@app.route("/api/cooldown", methods=["GET", "POST"])
def api_cooldown():
    """Retrieve 48-hour wishlist items or add a new impulse item."""
    user = get_current_user()

    if request.method == "GET":
        items = models.get_cooldown_items(user["id"])
        total_saved = models.get_total_cooldown_saved(user["id"])
        return jsonify({"status": "ok", "items": items, "total_saved": total_saved})

    data = request.get_json(silent=True) or {}
    item_name = str(data.get("item_name", "")).strip()
    if not item_name:
        return jsonify({"error": "Item name is required."}), 400

    try:
        amt = float(data.get("amount", 0))
        if amt <= 0:
            return jsonify({"error": "Amount must be greater than zero."}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid amount value."}), 400

    item = models.add_cooldown_item(user["id"], item_name, amt)
    return jsonify({"status": "created", "item": item}), 201


@app.route("/api/cooldown/<int:item_id>", methods=["PATCH"])
def api_patch_cooldown(item_id: int):
    """Resolve a cooldown item ('skipped' or 'bought')."""
    user = get_current_user()
    data = request.get_json(silent=True) or {}
    action = data.get("action")
    if action not in ("skipped", "bought"):
        return jsonify({"error": "Action must be 'skipped' or 'bought'."}), 400

    try:
        res = models.update_cooldown_item(item_id, user["id"], action)
        return jsonify(res)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404


def _build_ai_context(user: Dict[str, Any]) -> Dict[str, Any]:
    """Assemble complete real-time financial, budget, category, and recent expense context."""
    today_iso = datetime.date.today().strftime("%Y-%m-%d")
    metrics = models.calculate_safe_to_spend(user["id"])
    user_cats = models.get_categories(user["id"])
    active_categories = [c["name"] for c in user_cats] if user_cats else ["Food", "Travel", "Hostel/PG", "Fun", "Misc"]

    recent_raw = models.get_expenses(user_id=user["id"], limit=10)
    recent_expenses = []
    for r in recent_raw:
        recent_expenses.append({
            "id": r["id"],
            "date": r["expense_date"],
            "amount": r["amount"],
            "category": r["category"],
            "note": r["note"],
            "mood_tag": r["mood_tag"],
            "is_split": bool(r["is_split"]),
            "split_with": r.get("split_with", ""),
        })

    return {
        "today_date": today_iso,
        "active_categories": active_categories,
        "categories": active_categories,
        "monthly_budget": user["monthly_budget"],
        "total_spent_month": metrics["total_spent_month"],
        "spent_today": metrics["spent_today"],
        "safe_to_spend_today": metrics["safe_to_spend_today"],
        "days_remaining": metrics["days_remaining"],
        "category_totals": metrics["category_totals"],
        "mood_totals": metrics["mood_totals"],
        "pending_splits_total": models.get_pending_splits_total(user["id"]),
        "cooldown_saved_total": models.get_total_cooldown_saved(user["id"]),
        "recent_expenses": recent_expenses,
    }


def _execute_ai_action(user: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    """Execute real-world database mutations requested by Gemini (log, delete, cooldown, clarify, advice)."""
    action = result.get("action") or result.get("intent") or "advice"
    expense_logged = None
    expense_deleted = None
    cooldown_added = None

    if action == "log_expense" and result.get("expense"):
        exp_data = result["expense"]
        is_split = exp_data.get("split_count", 1) > 1
        exp_id = models.add_expense(
            user_id=user["id"],
            amount=exp_data["amount"],
            category=exp_data["category"],
            mood_tag=exp_data.get("mood_tag", "Essential"),
            is_split=is_split,
            split_count=exp_data.get("split_count", 1),
            split_with=exp_data.get("split_with", ""),
            note=exp_data.get("note", "AI Logged"),
            expense_date=exp_data.get("expense_date"),
        )
        logged_amt = round(exp_data["amount"] / exp_data.get("split_count", 1), 2) if is_split else exp_data["amount"]
        expense_logged = {
            "id": exp_id,
            "amount": logged_amt,
            "category": exp_data["category"],
            "mood_tag": exp_data.get("mood_tag", "Essential"),
            "note": exp_data.get("note", ""),
            "expense_date": exp_data.get("expense_date"),
            "is_split": is_split,
            "split_count": exp_data.get("split_count", 1),
            "split_with": exp_data.get("split_with", ""),
        }
        result["metrics"] = models.calculate_safe_to_spend(user["id"])

    elif action == "delete_last_expense":
        recent = models.get_expenses(user_id=user["id"], limit=1)
        if recent:
            last_exp = dict(recent[0])
            models.delete_expense(last_exp["id"], user["id"])
            expense_deleted = {
                "id": last_exp["id"],
                "amount": last_exp["amount"],
                "note": last_exp["note"],
                "category": last_exp["category"]
            }
            result["metrics"] = models.calculate_safe_to_spend(user["id"])

    elif action == "add_cooldown" and result.get("cooldown_item"):
        c_item = result["cooldown_item"]
        try:
            item_name = str(c_item.get("item_name") or "Impulse Item")
            amt = float(c_item.get("amount") or 500.0)
            saved_item = models.add_cooldown_item(user["id"], item_name, amt)
            cooldown_added = saved_item
        except Exception as e:
            print(f"[SmartSpend AI Error] add_cooldown failed: {e}")

    result["expense_logged"] = expense_logged
    result["expense_deleted"] = expense_deleted
    result["cooldown_added"] = cooldown_added
    result["intent"] = action
    result["mode"] = action
    return result


@app.route("/api/ai-status", methods=["GET"])
def api_ai_status():
    """Verify Gemini API configuration, connectivity status, and SDK installation."""
    return jsonify(ai_helper.check_ai_status())


@app.route("/api/ai-chat", methods=["POST"])
def api_ai_chat():
    """Interact with SmartSpend AI via text (Gemini 2.5 Flash with multi-turn conversation memory)."""
    user = get_current_user()
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()
    history = data.get("history") or []

    if not message:
        return jsonify({
            "action": "advice",
            "intent": "advice",
            "mode": "advice",
            "transcript": "",
            "reply": "Tell me what you spent or ask for budget advice!",
            "expense": None,
            "ai_mode": "fallback",
            "error_hint": None,
        })

    context = _build_ai_context(user)
    result = ai_helper.process_ai_text(message, context, history=history)
    result = _execute_ai_action(user, result)
    return jsonify(result)


@app.route("/api/ai-voice", methods=["POST"])
def api_ai_voice():
    """Handle 1-Button Voice commands using Gemini 2.5 Flash multimodal audio understanding."""
    user = get_current_user()
    context = _build_ai_context(user)

    history = []
    audio_bytes = None
    mime_type = "audio/webm"

    if "audio" in request.files:
        audio_file = request.files["audio"]
        audio_bytes = audio_file.read()
        raw_mime = audio_file.mimetype or "audio/webm"
        mime_type = raw_mime.split(";")[0].strip().lower()
        hist_raw = request.form.get("history")
        if hist_raw:
            try:
                history = json.loads(hist_raw)
            except Exception:
                history = []
    elif request.is_json:
        data = request.get_json(silent=True) or {}
        b64 = data.get("audio_base64")
        history = data.get("history") or []
        if b64:
            import base64
            audio_bytes = base64.b64decode(b64)
            raw_mime = data.get("mime_type", "audio/webm")
            mime_type = raw_mime.split(";")[0].strip().lower()

    if mime_type not in ["audio/webm", "audio/wav", "audio/mp3", "audio/mpeg", "audio/ogg", "audio/aac", "audio/flac"]:
        mime_type = "audio/webm"

    if not audio_bytes:
        return jsonify({"error": "No audio file received."}), 400

    result = ai_helper.process_ai_audio(audio_bytes, mime_type, context, history=history)
    result = _execute_ai_action(user, result)
    return jsonify(result)





# -------------------------------------------------------------------------
# CSV Exports
# -------------------------------------------------------------------------

@app.route("/api/export/<export_type>", methods=["GET"])
def api_export_csv(export_type: str):
    """Export expenses CSV file for personal record keeping."""
    clean_type = export_type.lower().strip()
    if clean_type != "expenses":
        return jsonify({"error": f"Invalid export type '{export_type}'. Allowed: expenses."}), 400

    conn = models.get_db()
    cursor = conn.cursor()
    output = io.StringIO()
    writer = csv.writer(output)

    if clean_type == "expenses":
        cursor.execute(
            """
            SELECT e.id, u.participant_code, e.amount, e.category, e.mood_tag, e.is_split, e.split_count,
                   e.owed_amount, e.split_settled, e.split_with, COALESCE(e.expense_date, date(e.created_at)) as expense_date,
                   e.note, e.created_at
            FROM expenses e
            JOIN users u ON e.user_id = u.id
            ORDER BY e.id ASC
            """
        )
        rows = cursor.fetchall()
        writer.writerow([
            "id", "participant_code", "amount", "category", "mood_tag", "is_split", "split_count",
            "owed_amount", "split_settled", "split_with", "expense_date", "note", "created_at"
        ])
        for r in rows:
            writer.writerow([
                r["id"], r["participant_code"], r["amount"], r["category"], r["mood_tag"],
                r["is_split"], r["split_count"], r["owed_amount"], r["split_settled"],
                r["split_with"], r["expense_date"], r["note"], r["created_at"]
            ])

    conn.close()

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=smartspend_expenses.csv"},
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
