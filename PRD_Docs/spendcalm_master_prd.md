# Master Product Requirements Document (PRD): SpendCalm

| Document Field | Details |
| :--- | :--- |
| **Product Name** | **SpendCalm** — *Emotion-Aware, Zero-Friction Web Expense Tracker* |
| **Document Version** | 2.0 (Production-Ready & Academic Specification) |
| **Institution & Course** | JG University — B.Tech Second Year Integrated Group Project |
| **Integrated Subjects** | Introduction to Design Thinking, Web Technology, Python, Probability & Statistics |
| **Team Size & Timeline** | 5 Students \| 6-Week Full Academic Lifecycle (with 1-Day MVP Sprint Guide) |
| **Primary Stack** | HTML5, CSS3, Vanilla JS, Chart.js, Python (Flask), SQLite, Google Gemini API |

---

## 1. Executive Summary & Strategic Vision

### 1.1 The Problem Space
Hostel and Paying Guest (PG) students living away from home operate on tight, fixed monthly discretionary budgets—typically **₹2,500 to ₹3,000** for food, snacks, local travel, and daily essentials. Most students currently use **no dedicated tracking tool**; they check their UPI or bank transaction history only 3 to 4 times a month. By then, dozens of micro-transactions (₹20 chai, ₹50 auto, ₹80 tiffin) blur together into **"mystery transactions"** where students see a depleted balance and cannot remember *where* or *why* their money disappeared.

Existing expense trackers fail this demographic due to two behavioral barriers:
1. **High Logging Friction:** Multi-step forms, nested menus, and mandatory fields turn a 10-second snack purchase into a tedious chore, leading to abandonment within a week.
2. **Negative Emotional Conditioning:** Cluttered spreadsheets and harsh red *"Budget Exceeded!"* alerts trigger financial anxiety, shame, and guilt—causing users to actively avoid opening the app.

### 1.2 The Product Vision
**SpendCalm** is a mobile-first, responsive web application engineered to reduce daily expense logging to **under 5 seconds** while transforming financial anxiety into calm clarity. It pairs zero-friction 1-tap presets and emotional mood tagging with a **Google Gemini AI Buddy** ("Chat-to-Log" and empathetic coaching). Crucially, SpendCalm includes an embedded **Usage Telemetry Engine** that automatically records task time, clicks, validation errors, and completion rates to statistically prove—with real experimental data—that SpendCalm outperforms existing tracking habits.

### 1.3 Competitive Differentiation Matrix
| Dimension | Checking UPI History (Current Habit) | Generic Expense Apps | **SpendCalm (Proposed Solution)** |
| :--- | :--- | :--- | :--- |
| **Logging Effort** | None, but zero context/labels | High (6–10 taps, multiple menus) | **Ultra-Low (1–2 taps or 1 chat sentence, $< 5\text{ s}$)** |
| **Memory Retention** | Poor (merchant names like *"Ramesh Enterprises"*) | Moderate (generic categories only) | **High (2-word Memory Anchor + Mood/Why Tag)** |
| **Emotional Tone** | Stressful surprises at month-end | Judgmental (harsh red warnings) | **Calm & Supportive (sage green/warm amber coach)** |
| **Student Utility** | No daily limit or friend split | Complex budgets, bloated UI | **Dynamic "Safe-to-Spend Today" + 1-Tap Friend Split** |
| **Academic Validation** | None | None | **Built-in Telemetry Engine + In-App SUS + CSV Export** |

### 1.4 Alignment with the 100-Mark Evaluation Rubric
| Evaluation Component | Marks | How SpendCalm Maximizes Marks |
| :--- | :---: | :--- |
| Problem Identification & Relevance | 8 | Hyper-specific hostel/PG student problem backed by lived friction (₹2,500–₹3,000 budget, mystery UPI spends). |
| Empathy & User Research | 12 | 5+ semi-structured interviews, Empathy Map, documented sampling plan, and $n \ge 30$ survey dataset. |
| Problem Definition & Statistical Insights | 15 | Persona, POV/HMW, MoSCoW, descriptive stats, Pearson/Spearman correlation, and baseline one-sample t-test. |
| Ideation & Creativity | 10 | 10+ brainstormed ideas, Mind Map, SWOT, Desirability/Feasibility/Viability matrix, emotion-first AI concept. |
| Prototype (Web Tech & Python) | 20 | Responsive calm UI, Flask + SQLite backend, Gemini AI Buddy, input validation, and automated telemetry logging. |
| Testing & Statistical Validation | 20 | Paired experiment ($n \ge 10$), Shapiro-Wilk normality check, paired t-test/Wilcoxon, $95\%$ CI, Cohen's $d$, SUS score, and V2 iterations. |
| Presentation, Documentation & Teamwork | 15 | Clean Git history across all 5 members, 20–50 page academic paper, 15–20 slide PPT, and live demo. |

---

## 2. Target Audience & Design Thinking Artifacts

### 2.1 Primary User Persona
* **Name:** Aarav Patel (Archetype Persona — Hostel/PG Student)
* **Age / Profile:** 20 years old, B.Tech 2nd Year student living in a PG 150 km away from home.
* **Monthly Discretionary Budget:** ₹3,000 (excluding fixed PG rent and mess fees).
* **Daily Spending Pattern:** 4–8 micro-transactions per day (morning chai ₹20, shared auto ₹50, canteen lunch ₹80, evening snacks ₹60, weekend outings ₹200).
* **Current Tracking Habit:** Checks GPay/PhonePe transaction history 3–4 times a month only when balance feels low.
* **Core Frustrations:**
  * *"I see ₹450 gone in two days and genuinely can't remember what I bought."*
  * *"I tried a budgeting app once, forgot to log for two days, saw a giant red bar, and uninstalled it."*
  * *"When I pay ₹300 for my friends' auto or pizza, apps think I spent ₹300 myself and ruin my budget."*
* **Goals:** Know in 2 seconds whether he can afford a treat today, stop forgetting small spends, and make his ₹3,000 last peacefully until the 30th.

### 2.2 Monthly Emotional User Journey Map (Current State)
| Timeline | Day 1–7 (Fresh Allowance) | Day 8–18 (Invisible Drift) | Day 19–25 (The Shock) | Day 26–30 (Survival Mode) |
| :--- | :--- | :--- | :--- | :--- |
| **Behavior** | Pays freely for snacks, outings, and friends' chai via UPI. | Makes 5+ small spends daily; never opens tracking tools. | Checks UPI history; sees only ₹400 left; tries to recall merchant names. | Skips outings, borrows from roommates, stresses about asking parents. |
| **Emotion** | Carefree, confident | Unaware, busy | Confused, anxious, guilty | Restricted, frustrated |
| **Opportunity** | Establish a daily Safe-to-Spend rhythm from Day 1. | Enable 3-second 1-tap logging + 2-word memory notes. | Replace guilt with a calm daily recovery adjustment. | Celebrate small daily savings and prevent end-of-month panic. |

### 2.3 Problem Framing Statements
* **Point of View (POV):** *A hostel/PG student living away from home needs an effortless, judgment-free way to capture small daily spends in under 5 seconds, because checking UPI history only a few times a month leaves them confused about forgotten transactions and anxious about running out of money.*
* **How Might We (HMW):** *How might we help hostel and PG students log micro-expenses in under 5 seconds and build awareness of their emotional spending triggers without inducing financial guilt?*

---

## 3. Success Metrics & KPIs

| Category | Metric | Baseline (Current Habit) | Target with SpendCalm | Measurement Method |
| :--- | :--- | :--- | :--- | :--- |
| **Efficiency** | Mean time to log 5 sample expenses | High / manual recall & notes | **$< 30\text{ seconds}$ total ($< 6\text{ s}$/entry)** | Built-in JS `performance.now()` telemetry |
| **Friction** | Mean clicks per 5-expense task | High / multi-screen switching | **$\le 15\text{ clicks}$ total** | Built-in JS click counter |
| **Accuracy** | Validation / input error rate | Manual typos & miscalculations | **$< 5\%$ error rate** | Built-in JS error counter |
| **Usability** | System Usability Scale (SUS) Score | Industry average = $68$ | **Mean SUS $\ge 75$ (Good–Excellent)** | In-app 10-question SUS form (`/feedback`) |
| **Emotional Impact** | User Satisfaction & Calmness (1–5) | Expected $< 3.0$ (below neutral) | **Mean $\ge 4.2$ / $5.0$** | Paired pre/post Likert comparison |
| **Statistical Proof** | Significance of Improvement | — | **$p < 0.05$ with medium-to-large effect ($d \ge 0.5$)** | Paired t-test / Wilcoxon in Python |

---

## 4. Detailed Functional Requirements & Acceptance Criteria

All features are prioritized using the **MoSCoW** framework and mapped directly to user needs.

### 4.1 MUST-HAVE Features (Core MVP)

#### F1. Anonymized Participant Onboarding & Budget Setup
* **User Story:** *As a student participant, I want to start using the app with an anonymized code and my monthly budget so my privacy is protected and my daily allowance is personalized.*
* **Functional Logic:**
  * On first visit (or via header profile switcher), display a clean onboarding modal requesting:
    1. `participant_code` (e.g., `P01`, `P02` — strictly no real names, emails, or phone numbers).
    2. `monthly_budget` (numeric input, default `3000`, valid range `100` to `100000`).
  * Persist active participant in Flask `session` and SQLite `users` table. Returning codes load existing expenses seamlessly.
* **Acceptance Criteria:**
  * Rejects empty participant codes or non-positive budgets with friendly inline validation.
  * Displays an explicit one-line ethics reminder: *"Privacy first: Please use an anonymized ID (e.g., P01), not your real name."*

#### F2. Calm "Safe-to-Spend Today" Hero Dashboard
* **User Story:** *As a hostel student, I want to see one clear number telling me how much I can safely spend today so I do not have to do stressful mental math.*
* **Calculation Formula:**
  Let $B$ be the monthly budget, $S_{\text{month}}$ be total expenses logged in the current calendar month, and $D_{\text{rem}}$ be the number of days remaining in the month inclusive of today ($D_{\text{rem}} \ge 1$):
  $$
  \text{Safe-to-Spend Today} = \max\left(0, \frac{B - S_{\text{month}}}{D_{\text{rem}}}\right)
  $$
  Let $S_{\text{today}}$ be total expenses logged today, and $L_{\text{start}}$ be the daily allowance at the start of today:
  $$
  L_{\text{start}} = \max\left(0, \frac{B - (S_{\text{month}} - S_{\text{today}})}{D_{\text{rem}}}\right), \qquad \text{Remaining Today} = L_{\text{start}} - S_{\text{today}}
  $$
* **Edge Cases:**
  * **Last day of month:** $D_{\text{rem}} = 1$ (never divide by zero).
  * **Overspent today ($\text{Remaining Today} < 0$):** Display `₹0 left today`, switch card accent from Sage Green (`#10B981`) to Warm Amber (`#F59E0B`), and trigger the Gentle Recovery Coach.
  * **Monthly budget exhausted ($S_{\text{month}} \ge B$):** Display `₹0` with calm guidance rather than negative red numbers.
* **Acceptance Criteria:**
  * Updates dynamically via Fetch API without full page reload whenever an expense is added or deleted.
  * Displays monthly progress bar (`%` of budget used) and a daily logging streak badge (consecutive days with $\ge 1$ log).

#### F3. 5-Second Rapid Expense Logger (No-Scroll Home Bar)
* **User Story:** *As a busy student, I want to log a ₹20 chai or ₹80 meal in under 5 seconds right from the home screen so I never forget small transactions.*
* **Functional Logic:**
  * Positioned directly beneath the Hero Card on `/` (no hidden menus or modal pop-ups).
  * **1-Tap Hostel Presets:** Clicking a preset chip (`₹20 Chai`, `₹50 Auto`, `₹80 Tiffin`, `₹100 Snacks`) auto-fills Amount, selects the matching Category, selects default Mood (`Essential` or `Craving`), and focuses the Save button.
  * **Category Chips (Single Select):** `Food`, `Travel`, `Hostel/PG`, `Fun`, `Misc`.
  * **2-Word Memory Anchor:** Optional text input (`maxlength="60"`, placeholder: *"Quick memory note, e.g., Canteen w/ Raj"*).
  * **Validation:** Client-side and server-side checks ensure `amount > 0`, valid category, and valid mood tag. Invalid attempts increment the telemetry `error_count` during Test Mode.
* **Acceptance Criteria:**
  * Logging a preset expense takes at most **2 clicks** (1 tap preset + 1 tap *"Save & Done"*).
  * Triggers a smooth toast notification showing elapsed seconds (e.g., *"Logged in 3.2s! You won't forget this one."*).

#### F4. Mood & "Why" Tagging System
* **User Story:** *As a student trying to build better habits, I want to tag the emotional reason behind a purchase so I can see if boredom or stress is draining my wallet.*
* **Tag Taxonomy:**
  * `Essential` — Daily necessities (tiffin, auto, stationery).
  * `Craving` — Late-night snacks, cravings, or boredom eating.
  * `Friends` — Group outings, shared chai, social memories.
  * `Impulse` — Unplanned online or canteen purchases.
* **Acceptance Criteria:**
  * Selected via large pill-shaped toggle buttons (minimum `44px` height).
  * Defaults to `Essential` so logging stays fast if the user does not wish to change it.

#### F5. Gentle Recovery Coach (Empathetic Microcopy Engine)
* **User Story:** *As a student on a tight budget, I want supportive suggestions when I overspend instead of alarming red warnings that make me feel guilty.*
* **Dynamic Copy Rules:**
  * **On Track ($S_{\text{today}} \le 0.8 \cdot L_{\text{start}}$):** *"You're cruising smoothly! ₹{Remaining} is comfortably safe for the rest of today."*
  * **Approaching Limit ($0.8 \cdot L_{\text{start}} < S_{\text{today}} \le L_{\text{start}}$):** *"Almost at today's calm limit—₹{Remaining} left for tonight."*
  * **Over Daily Limit ($S_{\text{today}} > L_{\text{start}}$):** Calculate excess $E = S_{\text{today}} - L_{\text{start}}$ and recovery window $W = \min(4, \max(1, D_{\text{rem}} - 1))$, with daily trim $T = \lceil E / W \rceil$. Display: *"A little over today—no stress. Trimming ₹{T}/day for the next {W} days gets you right back on track."*
* **Acceptance Criteria:**
  * Never uses the words *"Warning"*, *"Alert"*, *"Failed"*, or *"Exceeded"*.

#### F6. Visual Analytics & Auto-Generated Story Insights
* **User Story:** *As a student, I want simple visual charts and a 1-sentence takeaway so I immediately understand my spending patterns.*
* **Functional Logic:**
  * **Chart 1 (Doughnut):** Spending distribution across the 5 Categories (`Chart.js`).
  * **Chart 2 (Horizontal Bar):** Spending distribution across the 4 Mood Tags (`Chart.js`).
  * **Auto Story Insight:** Backend computes the highest non-essential mood tag and highest category, returning a plain-English insight (e.g., *"Heads up: 'Craving' spends totaled ₹540 this month—24% of your budget."*).
* **Acceptance Criteria:**
  * Charts resize cleanly across mobile and desktop viewports and show friendly empty states when 0 expenses exist.

#### F7. Searchable Transaction History
* **Functional Logic:**
  * Displays expenses in reverse chronological order with amount, category badge, mood tag, 2-word memory anchor, split badge (if split), and timestamp.
  * Live search bar (filters by memory note) + quick filter pills by Category or Mood Tag.
  * Delete button (`DELETE /api/expenses/<id>`) removes the record and refreshes dashboard metrics and charts immediately.

#### F8. Built-In Usage Telemetry & Usability Experiment Mode (`/test-mode`)
* **Purpose:** Directly fulfills Stage 4 ("Built-in measurement") and Stage 5 ("Statistical validation") of the assignment brief.
* **Functional Logic:**
  * Displays an instruction card with a standardized **5-Expense Student Test Scenario** (see Section 8.2) and a **"Start Timed Task"** button.
  * **Silent JavaScript Telemetry (`telemetry.js`):**
    * Starts high-precision timer (`t0 = performance.now()`) on clicking "Start Timed Task".
    * Counts every user click inside the task container (`click_count`).
    * Increments `error_count` whenever a form submission fails validation (empty/negative amount) or an incorrect amount is cleared.
    * Tracks progress (`1/5` to `5/5` logged). Upon the 5th valid log, calculates `time_taken_sec = (performance.now() - t0) / 1000`, sends payload to `POST /api/telemetry`, and reveals a completion summary card with a direct link to `/feedback`.
  * Includes an **"Abandon / Reset Task"** button that logs `completed = 0` if a participant gives up.
* **Acceptance Criteria:**
  * Accurately persists `participant_code`, `task_name`, `time_taken_sec`, `click_count`, `error_count`, and `completed` to SQLite `usage_telemetry`.

#### F9. In-App System Usability Scale (SUS) Survey (`/feedback`)
* **Functional Logic:**
  * Renders all **10 standardized SUS items** on a 5-point Likert scale (`1 = Strongly Disagree` to `5 = Strongly Agree`):
    1. *I think that I would like to use SpendCalm frequently.*
    2. *I found SpendCalm unnecessarily complex.*
    3. *I thought SpendCalm was easy to use.*
    4. *I think that I would need the support of a technical person to be able to use SpendCalm.*
    5. *I found the various functions in SpendCalm were well integrated.*
    6. *I thought there was too much inconsistency in SpendCalm.*
    7. *I would imagine that most people would learn to use SpendCalm very quickly.*
    8. *I found SpendCalm very cumbersome to use.*
    9. *I felt very confident using SpendCalm.*
    10. *I needed to learn a lot of things before I could get going with SpendCalm.*
  * Plus: **Overall Satisfaction Rating** ($1$–$5$), **Emotional Comfort Rating** (*"Did SpendCalm feel calmer than checking UPI/other apps?"*, $1$–$5$), and an **Open-Ended Feedback** textarea.
  * **Python SUS Computation:**
    $$
    \text{SUS} = 2.5 \times \left( \sum_{i \in \{1,3,5,7,9\}} (x_i - 1) + \sum_{j \in \{2,4,6,8,10\}} (5 - x_j) \right)
    $$
* **Acceptance Criteria:**
  * Validates all 10 SUS items are answered before submission; stores both raw score and computed $0$–$100$ SUS score in SQLite `sus_feedback`.

#### F10. 1-Click Anonymized CSV Export
* **Functional Logic:**
  * Admin/Researcher export endpoints (`/api/export/telemetry`, `/api/export/sus`, `/api/export/expenses`) stream properly formatted `.csv` files with headers and `Content-Disposition: attachment` using Python's built-in `csv` module.
* **Acceptance Criteria:**
  * Contains zero personally identifiable information (only `participant_code`). Opens cleanly in Python `pandas.read_csv()` and Excel.

---

### 4.2 SHOULD-HAVE Features (High-Impact Differentiators)

#### F11. AI Assistant — "SpendCalm Buddy" (Google Gemini API)
* **User Story:** *As a student walking back from the canteen, I want to just type "spent 120 on biryani with 2 friends" or ask "can I afford pizza tonight?" and let the AI log it or advise me calmly.*
* **Functional Logic:**
  * Sleek floating circular button (`bottom-right`) opens a non-intrusive slide-up chat drawer on all pages.
  * Includes 3 quick-tap starter chips: `"Log ₹30 chai with friends"`, `"Split ₹180 auto with 2 roommates"`, `"Can I afford a ₹200 treat today?"`.
  * Backend (`ai_helper.py`) calls `gemini-2.5-flash` via the `google-genai` SDK with structured JSON output enforcement (exact prompt & schema in Section 6.4).
  * **Mode 1 (`log_expense`):** Extracts `amount`, `category`, `mood_tag`, `split_count`, and `note`, applies split division if `split_count > 1`, inserts directly into SQLite `expenses`, and refreshes the dashboard live.
  * **Mode 2 (`advice`):** Uses injected real-time user context (`monthly_budget`, `total_spent`, `safe_to_spend_today`, `top_mood_spend`) to give a 2–3 sentence empathetic response.
  * **Resilience Fallback:** If `GEMINI_API_KEY` is missing, rate-limited, or offline, returns HTTP 200 with a polite fallback message (*"SpendCalm Buddy is taking a quick nap—your 1-tap presets above still work instantly!"*). Never throws an unhandled 500 error.

#### F12. 1-Tap Roommate / Group Split
* **User Story:** *As a hostel resident who frequently pays the full auto fare or food bill for friends, I want to split the cost right inside the logger so only my share counts against my budget.*
* **Functional Logic:**
  * Toggle switch *"Split with friends?"* reveals a compact stepper (`Split by: 2, 3, 4...`).
  * Live preview shows: *"Your share: ₹{round(amount / N, 2)}"*.
  * Stores the user's share as `amount`, sets `is_split = 1`, `split_count = N`, and appends `(Split ÷ N)` metadata in the UI.

---

### 4.3 COULD-HAVE Features (Stretch Goals)

#### F13. 48-Hour Impulse Cooldown Wishlist (`/cooldown`)
* **User Story:** *When I feel tempted to buy something non-essential online, I want to park it for 48 hours so I can check later if I actually still want it.*
* **Functional Logic:**
  * Users add `item_name` and `amount`; backend sets `unlock_at = created_at + 48 hours` and `status = 'waiting'`.
  * Cards display a live JS countdown (`47h 59m left`).
  * Two action buttons: **"Skipped It! (Save Money)"** (marks `skipped` and adds amount to a celebratory *"Total Impulse Money Saved"* banner) or **"Still Want It (Log Now)"** (marks `bought` and logs an `Impulse` expense).

### 4.4 WON'T-HAVE Features (Strict Scope Boundary)
* Direct bank/UPI SMS scraping or RBI-regulated Account Aggregator APIs.
* Mutual fund, stock, or crypto tracking.
* Multi-currency conversion or complex recurring loan/EMI calculators.

---

## 5. Emotion-First UI/UX Design System

### 5.1 Design Tokens (CSS Variables)
```css
:root {
  --bg-page: #F8FAFC;          /* Calm off-white canvas */
  --bg-card: #FFFFFF;          /* Crisp elevated card */
  --border-subtle: #E2E8F0;    /* Soft divider */
  --text-primary: #1E293B;     /* Deep slate for high legibility */
  --text-muted: #64748B;       /* Cool gray secondary copy */
  --safe-primary: #10B981;     /* Soft sage green (On track) */
  --safe-tint: #ECFDF5;        /* Light mint wash */
  --caution-primary: #F59E0B;  /* Warm amber (Over limit - NO HARSH RED) */
  --caution-tint: #FFFBEB;     /* Soft warm cream wash */
  --brand-indigo: #4F46E5;     /* Subtle accent for AI Buddy & active nav */
  --radius-card: 16px;
  --radius-pill: 9999px;
  --shadow-card: 0 4px 20px rgba(15, 23, 42, 0.05);
  --font-main: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
}
```

### 5.2 Screen Layout Blueprint (Mobile-First Responsive)
```text
+--------------------------------------------------+
|  SpendCalm    [P01 | ₹3,000]   [Dash|Cool|Test]  |  <-- Clean Sticky Navbar
+--------------------------------------------------+
|  SAFE TO SPEND TODAY                 🔥 4d streak|
|  ₹92.50                                          |  <-- Hero Card (Calm Green/Amber)
|  [=============-------] 54% of ₹3,000 used       |
|  "You're cruising smoothly! ₹92.50 left today."  |
+--------------------------------------------------+
|  QUICK LOG (< 5 SECONDS)                         |
|  [☕ ₹20 Chai] [🛺 ₹50 Auto] [🍱 ₹80] [🍔 ₹100]  |  <-- 1-Tap Preset Chips (>=44px)
|  Amount: [ ₹ ______ ]  Note: [ Canteen w/ Raj ]  |
|  Category: (Food) (Travel) (Hostel) (Fun) (Misc) |  <-- Pill Selectors
|  Mood:     (🟢Ess) (🍕Crav) (🤝Frnd) (⚡Impls)   |
|  [ ] Split with friends?     [  Save & Done  ]   |
+--------------------------------------------------+
|  SPENDING INSIGHTS                               |
|  [ Category Doughnut ]    [ Mood Horizontal Bar ]|  <-- 2-Col on Desktop, Stacked Mobile
|  💡 "Craving spends totaled ₹420 this month."    |
+--------------------------------------------------+
|  RECENT HISTORY                [Search notes...] |
|  🍱 ₹80  Food  • Essential • "Mess lunch"    [x] |
|  ☕ ₹20  Food  • Friends   • "Chai w/ Aman"  [x] |
+--------------------------------------------------+
                                     ( ✨ AI Buddy ) <-- Floating Chat Drawer Trigger
```

### 5.3 Micro-Interactions & Accessibility Rules
* **Tactile Feedback:** All chips and buttons have `transition: all 0.2s ease`, subtle scale press (`transform: scale(0.97)` on `:active`), and clear focus rings (`outline: 2px solid var(--brand-indigo)`) for keyboard navigation.
* **Toast Notifications:** Non-blocking top-right/bottom-center toast auto-dismisses after `3.5s`.
* **WCAG AA Compliance:** All text/background pairs maintain a minimum contrast ratio of `4.5:1`. Every icon button includes `aria-label` attributes.

---

## 6. Technical Architecture, Database & API Specifications

### 6.1 System Architecture Flow
```text
[Mobile / Desktop Browser]
  │  HTML5 / CSS3 / Vanilla JS / Chart.js / telemetry.js
  ▼  (JSON over HTTP Fetch API)
[Flask Web Server (app.py)]
  ├──► [SQLite Database (database.db)]  ◄── Stores users, expenses, cooldown, telemetry, SUS
  ├──► [Google Gemini API (ai_helper.py)] ◄── gemini-2.5-flash (Chat-to-Log & Calm Advice)
  └──► [CSV Streamer (/api/export/*)]   ──► [Python Analysis (validate_stats.py: Pandas/SciPy)]
```

### 6.2 Complete SQLite Database Schema (`models.py`)
```sql
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    participant_code TEXT UNIQUE NOT NULL,
    monthly_budget REAL NOT NULL DEFAULT 3000.0 CHECK (monthly_budget > 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount REAL NOT NULL CHECK (amount > 0),
    category TEXT NOT NULL CHECK (category IN ('Food', 'Travel', 'Hostel/PG', 'Fun', 'Misc')),
    mood_tag TEXT NOT NULL CHECK (mood_tag IN ('Essential', 'Craving', 'Friends', 'Impulse')),
    is_split INTEGER NOT NULL DEFAULT 0 CHECK (is_split IN (0, 1)),
    split_count INTEGER NOT NULL DEFAULT 1 CHECK (split_count >= 1),
    note TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS cooldown_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    item_name TEXT NOT NULL,
    amount REAL NOT NULL CHECK (amount > 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    unlock_at TIMESTAMP NOT NULL,
    status TEXT NOT NULL DEFAULT 'waiting' CHECK (status IN ('waiting', 'bought', 'skipped')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS usage_telemetry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    participant_code TEXT NOT NULL,
    task_name TEXT NOT NULL,
    time_taken_sec REAL NOT NULL CHECK (time_taken_sec >= 0),
    click_count INTEGER NOT NULL CHECK (click_count >= 0),
    error_count INTEGER NOT NULL CHECK (error_count >= 0),
    completed INTEGER NOT NULL CHECK (completed IN (0, 1)),
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sus_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    participant_code TEXT NOT NULL,
    q1 INTEGER NOT NULL, q2 INTEGER NOT NULL, q3 INTEGER NOT NULL,
    q4 INTEGER NOT NULL, q5 INTEGER NOT NULL, q6 INTEGER NOT NULL,
    q7 INTEGER NOT NULL, q8 INTEGER NOT NULL, q9 INTEGER NOT NULL,
    q10 INTEGER NOT NULL,
    sus_score REAL NOT NULL CHECK (sus_score >= 0 AND sus_score <= 100),
    satisfaction_rating INTEGER NOT NULL CHECK (satisfaction_rating BETWEEN 1 AND 5),
    calmness_rating INTEGER NOT NULL DEFAULT 3 CHECK (calmness_rating BETWEEN 1 AND 5),
    qualitative_feedback TEXT DEFAULT '',
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_expenses_user_date ON expenses(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_telemetry_participant ON usage_telemetry(participant_code);
```

### 6.3 REST API Contract Specification
| Method | Endpoint | Request Payload (JSON) | Success Response (`200` / `201`) | Error Codes |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/session` | `{"participant_code": "P01", "monthly_budget": 3000}` | `{"status": "ok", "user": {...}}` | `400` Invalid input |
| `GET` | `/api/dashboard` | *(Session cookie)* | `{"safe_today": 92.5, "remaining_today": 72.5, "status_tone": "safe", "coach_message": "...", "streak": 4, "category_totals": {...}, "mood_totals": {...}, "story_insight": "...", "expenses": [...]}` | `401` No session |
| `POST` | `/api/expenses` | `{"amount": 120, "category": "Food", "mood_tag": "Friends", "is_split": true, "split_count": 3, "note": "Biryani w/ Raj"}` | `{"status": "created", "logged_amount": 40.0, "expense_id": 12}` | `400` Validation fail |
| `DELETE` | `/api/expenses/<id>` | *(None)* | `{"status": "deleted", "id": 12}` | `404` Not found |
| `POST` | `/api/cooldown` | `{"item_name": "Gaming Mouse", "amount": 799}` | `{"status": "created", "item": {...}}` | `400` Invalid input |
| `PATCH` | `/api/cooldown/<id>` | `{"action": "skipped"}` or `{"action": "bought"}` | `{"status": "updated", "total_saved": 799}` | `404` Not found |
| `POST` | `/api/ai-chat` | `{"message": "spent 60 on auto to college"}` | `{"mode": "log_expense", "reply": "Got it! Logged ₹60...", "expense_logged": {...}}` | `200` Graceful fallback |
| `POST` | `/api/telemetry` | `{"participant_code": "P01", "task_name": "log_5_expenses", "time_taken_sec": 21.4, "click_count": 12, "error_count": 0, "completed": 1}` | `{"status": "recorded", "id": 5}` | `400` Missing fields |
| `POST` | `/api/feedback` | `{"participant_code": "P01", "answers": [5,1,5,1,4,1,5,1,5,1], "satisfaction_rating": 5, "calmness_rating": 5, "qualitative_feedback": "..."}` | `{"status": "saved", "sus_score": 97.5}` | `400` Incomplete SUS |
| `GET` | `/api/export/<type>` | `<type>` in `telemetry`, `sus`, `expenses` | Streamed `.csv` file download | `400` Invalid type |

### 6.4 Google Gemini AI Assistant Prompt & JSON Schema (`ai_helper.py`)
* **Model:** `gemini-2.5-flash` via `google-genai` SDK with `response_mime_type="application/json"`.
* **System Instruction:**
  > *"You are SpendCalm Buddy, a warm, non-judgmental financial friend for an Indian hostel/PG college student. Never shame or lecture the user. Always respond strictly in valid JSON matching the requested schema. Use the provided real-time budget context (`monthly_budget`, `total_spent`, `safe_to_spend_today`, `mood_totals`). If the user describes a purchase or spend, set `mode` to `log_expense`, extract `amount` (total paid before split), `split_count` (default 1; if they say 'with 2 friends', total people = 3), `category` (one of: Food, Travel, Hostel/PG, Fun, Misc), `mood_tag` (one of: Essential, Craving, Friends, Impulse), and a 2–4 word `note`. If they ask a question or want advice, set `mode` to `advice` and write a calm, practical 2–3 sentence `reply` referencing their exact Rupee numbers."*
* **Expected JSON Output Schema:**
  ```json
  {
    "mode": "log_expense | advice",
    "reply": "Got it! Logged ₹40 (your share of ₹120) under Food. You still have ₹52.50 safe to spend today.",
    "expense": {
      "amount": 120,
      "split_count": 3,
      "category": "Food",
      "mood_tag": "Friends",
      "note": "Biryani with friends"
    }
  }
  ```
  *(When `mode` is `"advice"`, `"expense"` is `null`.)*

---

## 7. Non-Functional Requirements (NFRs)

* **Performance:** Local dashboard load $< 300\text{ ms}$; expense logging API response $< 100\text{ ms}$; AI Buddy response $< 3\text{ s}$ with animated typing indicator.
* **Responsiveness:** Mobile-first CSS supporting screen widths from `360px` (standard Android phones) to `1440px+` (laptops/projectors for viva demo).
* **Security & Privacy:**
  * Parameterized SQL queries everywhere (zero SQL injection risk).
  * `GEMINI_API_KEY` loaded strictly via `os.getenv()` from `.env`; `.env` explicitly listed in `.gitignore`.
  * Strict participant anonymization (`P01`, `P02`); informed consent text presented before data collection.
* **Code Quality & Maintainability:** Modular Python files, docstrings on all route handlers and helper functions, clean error handling (`try/except` with informative JSON errors), and a complete `README.md` with setup instructions.

---

## 8. Usability Testing Protocol & Statistical Validation Blueprint

### 8.1 Stage 2: Baseline Problem Validation ($n \ge 30$ Survey)
* **Sampling Method:** Stratified convenience sampling across hostel and PG students (Document limitations: single-university bias, self-reported recall error).
* **Required Analyses (`validate_stats.py`):**
  1. **Descriptive Statistics:** Mean, median, mode, standard deviation, IQR, histograms, and box plots of monthly budget, frequency of forgetting transactions, and current satisfaction.
  2. **Correlation Analysis:** Pearson's $r$ (or Spearman's $\rho$ for ordinal Likert data) between *frequency of forgotten spends* and *monthly financial anxiety score*.
  3. **Baseline One-Sample Hypothesis Test ($\alpha = 0.05$):**
     * $H_0: \mu_{\text{CurrentSat}} \ge 3.0$ (Students are neutral or satisfied with current UPI/manual tracking).
     * $H_1: \mu_{\text{CurrentSat}} < 3.0$ (Students are significantly dissatisfied).
     * Report $t$-statistic, $p$-value, and $95\%$ confidence interval.

### 8.2 Stage 5: Standardized Paired Usability Experiment ($n \ge 10$ Participants)
* **Design:** Within-subjects paired design (same 10+ hostel/PG students complete both conditions; alternate starting order across odd/even participants to minimize learning/order bias).
* **Standardized 5-Expense Task Card (Identical for Both Conditions):**
  1. Morning chai at college gate — **₹20** (`Food`, `Essential`)
  2. Shared auto to campus — **₹50** (`Travel`, `Essential`)
  3. Mess/Tiffin lunch — **₹80** (`Food`, `Essential`)
  4. Late-night chips craving — **₹40** (`Food`, `Craving`)
  5. Pizza paid for 3 friends — **₹300 total, split 3 ways = ₹100 share** (`Food`, `Friends`)
* **Condition A (Baseline — Current Method):** Participant records and totals these 5 items (including their split share) using their current habit (Notes app / Calculator / Excel) while timed externally with a stopwatch; rates satisfaction ($1$–$5$).
* **Condition B (Prototype — SpendCalm `/test-mode`):** Participant logs the same 5 items in SpendCalm while `telemetry.js` automatically captures exact time, clicks, errors, and completion; submits `/feedback` SUS & satisfaction score.

### 8.3 Stage 5 Statistical Tests & Decision Tree ($\alpha = 0.05$)
* **Pre-Registered Hypotheses (Written in Stage 3 before testing):**
  * **Efficiency:** $H_0: \mu_{\text{Time, SpendCalm}} \ge \mu_{\text{Time, Baseline}}$ vs. $H_1: \mu_{\text{Time, SpendCalm}} < \mu_{\text{Time, Baseline}}$.
  * **Satisfaction:** $H_0: \mu_{\text{Sat, SpendCalm}} \le \mu_{\text{Sat, Baseline}}$ vs. $H_1: \mu_{\text{Sat, SpendCalm}} > \mu_{\text{Sat, Baseline}}$.
  * **Completion / Preference:** Chi-square test or exact binomial proportion test with $95\%$ Wilson confidence interval.
* **Assumption Checking:** Run **Shapiro-Wilk test** on paired differences ($d_i = x_{i,\text{SpendCalm}} - x_{i,\text{Baseline}}$).
  * If $p_{\text{Shapiro}} > 0.05$ (normal): Execute **Paired Samples t-test** and compute **Cohen's $d$** effect size.
  * If $p_{\text{Shapiro}} \le 0.05$ (non-normal): Execute **Wilcoxon Signed-Rank test** and compute rank-biserial correlation $r$.
* **Iteration Requirement (Version 1 $\to$ Version 2):** Document at least **3 real usability issues** observed during testing (e.g., unclear split toggle placement, preset chip label confusion, mobile keyboard covering the Save button), implement fixes in Version 2, and present Before/After screenshots in the PPT and Research Paper.

---

## 9. Risk Management & Mitigation Matrix

| Risk | Severity | Mitigation Strategy |
| :--- | :---: | :--- |
| **Gemini API offline or rate-limited during live Viva** | High | Keep all core features (1-tap presets, logger, charts, telemetry) 100% local in Flask/SQLite; display a graceful AI fallback message so the demo never crashes. |
| **Leaking `GEMINI_API_KEY` on public GitHub** | High | Enforce `.env` in `.gitignore` on Day 1 and commit only `.env.example`. |
| **Test data fails normality assumption** | Medium | Pre-plan Shapiro-Wilk check in `validate_stats.py` and automatically fall back to Wilcoxon Signed-Rank test with clear explanation. |
| **Prototype shows smaller-than-expected improvement** | Low | Per Section 13 of the brief, report honest results, analyze *why* (e.g., unfamiliarity with new UI on first try), and document V2 UI improvements—honest negative/mixed results earn full academic credit. |
| **Uneven Git commits across 5 team members** | Medium | Use feature branches (`feat/frontend-ui`, `feat/backend-api`, `feat/stats-scripts`) so every student has verified commits before Week 6. |

---

## 10. Team Governance & Execution Roadmap

### 10.1 Team Roles & Technical Ownership (5 Members)
| Role | Core Design & Academic Deliverables | Mandatory Technical Contribution |
| :--- | :--- | :--- |
| **1. Research Lead** | 5+ interviews, Empathy Map, Persona, POV/HMW, consent forms | Assists with survey logic & qualitative coding |
| **2. Statistics Lead** | 30+ survey design, sampling plan, baseline & Stage 5 validation | Writes `analysis/validate_stats.py` (Pandas, SciPy, Matplotlib) |
| **3. Frontend Lead** | Wireframes (Paper/Figma), calm responsive UI, accessibility | Builds `style.css`, `app.js`, Chart.js, and `telemetry.js` |
| **4. Backend Lead** | System architecture, SQLite schema, Git repo management | Builds `app.py`, `models.py`, `ai_helper.py`, CSV exports |
| **5. Project & Doc Lead** | Timeline, Mind Map/SWOT, 20–50p Paper, 15–20 slide PPT | Runs Stage 5 testing sessions & compiles SUS feedback |

### 10.2 Full 6-Week Academic Roadmap
* **Week 1:** Submit 1-page topic proposal; finalize ethics consent form, 30+ survey questionnaire, and GitHub repo setup.
* **Week 2:** Conduct 5–7 user interviews and collect $n \ge 30$ survey responses; build Empathy Map.
* **Week 3:** Clean data in Python; generate descriptive stats, correlations, and baseline hypothesis test; finalize Persona, POV, HMW, and MoSCoW.
* **Week 4:** Brainstorm 10+ ideas, SWOT, pre-register Stage 5 hypotheses; complete wireframes and build core Flask + Frontend MVP.
* **Week 5:** Integrate Gemini AI Buddy, `/test-mode` telemetry, and `/feedback` SUS; execute paired usability tests ($n \ge 10$); implement 3+ V2 fixes; run statistical validation.
* **Week 6:** Finalize live demo, verify Git commits across all 5 members, submit Research Paper & PPT, and rehearse the 10–12 min presentation + 5 min viva Q&A.

### 10.3 Rapid 1-Day MVP Build Sprint (Using Antigravity)
1. **Hour 1 — Scaffold & DB:** Initialize Flask, `models.py` (SQLite schema), and anonymized onboarding session.
2. **Hour 2–3 — Emotion-First UI & Core Logger:** Build the calm Hero Card, 1-tap hostel presets, mood tags, roommate split, Chart.js graphs, and searchable history.
3. **Hour 4 — AI Buddy & Cooldown:** Connect `ai_helper.py` to Google AI Studio (`gemini-2.5-flash`) with `.env` key and fallback handling; add `/cooldown`.
4. **Hour 5 — Telemetry, SUS & Exports:** Build `/test-mode` (`telemetry.js`), `/feedback` (10-item SUS calculator), and `/api/export/*` CSV downloads.
5. **Hour 6 — End-to-End QA & Pilot Test:** Test mobile responsiveness (`360px` width), verify SQLite telemetry rows and CSV exports, and push cleanly to GitHub.