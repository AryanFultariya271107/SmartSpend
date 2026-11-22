# SmartSpend: AI-Powered Personal Budget Tracker

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.x-green.svg)](https://flask.palletsprojects.com/)
[![Google Gemini API](https://img.shields.io/badge/Google%20GenAI-gemini--2.5--flash-orange.svg)](https://ai.google.dev/)
[![SQLite](https://img.shields.io/badge/Database-SQLite3-lightgrey.svg)](https://www.sqlite.org/)
[![Design System](https://img.shields.io/badge/Design-Editorial%20Fintech-1B4332.svg)](#design-system--aesthetics)

> **Emotion-Aware, Zero-Friction Web Expense Tracker & Usability Validation Suite for College Hostel & PG Students**

SmartSpend is an integrated personal finance web application built to eliminate the **"mystery transactions"** phenomenon common among college hostel and PG students living on tight daily budgets (typically ₹2,500–₹3,000/month). By replacing tedious multi-step forms and negative emotional conditioning (harsh red alerts) with **< 5-second rapid logging**, **1-button voice expense capture**, a **72px icon-only mini rail**, a **Google Gemini AI Assistant (SmartSpend AI)**, and an interactive **Monthly Spending Calendar**, SmartSpend transforms budgeting from an anxiety trigger into a calm daily habit.

---

## Key Highlights

- **Google AI Studio (Gemini 2.5 Flash):** Natural language expense logging and financial coaching via the official `google-genai` Python SDK, with multi-turn chat, context-aware budget guidance, and an offline rule-based fallback engine.
- **1-Button Voice Logging:** Speak or type natural commands (e.g. *"20 rs for chai from Sharma shop"*, *"split 240 pizza with Raj and Amit"*) to automatically extract amount, merchant note, category, intent, date, and split count.
- **Safe-to-Spend Today Metric:** Dynamically recalculates daily spending pace with zero red panic alerts; overspending triggers a **Gentle Recovery Coach** suggesting a multi-day trim.
- **72px Icon-Only Mini Rail (Desktop):** Collapsible desktop navigation that smoothly transitions into an icon rail with floating dark tooltips, paired with an off-canvas slide-over drawer on mobile.
- **Impulse Cooldown Wishlist:** A 48-hour parking tank for impulsive shopping desires with live countdown timers and total money saved metrics.
- **Hostel Splits & Bills Ledger:** Shared expenses, roommate settlement tracking, and monthly recurring bills.
- **Academic Statistical Validation:** Built-in empirical validation suite with paired t-tests, Cohen's d effect size, and System Usability Scale (SUS) analysis.

---

## Project Architecture

```text
expence traker/
├── app.py                     # Main Flask application, page routes, REST APIs, CSV exports
├── models.py                  # Auto-init SQLite database engine, Safe-to-Spend math, streaks, splits
├── ai_helper.py               # Google Gemini API client (google-genai SDK) & offline parser
├── database.db                # SQLite database (auto-initialized on startup)
├── requirements.txt           # Python dependencies (flask, google-genai, scipy, etc.)
├── .env.example               # Template for environment variables (GEMINI_API_KEY)
├── .env                       # Local secrets (never committed to git)
├── .gitignore                 # Excludes .env, database.db, .venv/, __pycache__/, charts/
├── README.md                  # Complete project documentation & guide
├── PRD_Docs/                  # Product Requirements Document & design specifications
├── analysis/
│   ├── validate_stats.py      # Statistical evaluation suite (paired t-test, Cohen's d, SUS)
│   ├── baseline_survey.csv    # Stage 2 student baseline survey dataset (n=35)
│   ├── paired_experiment.csv  # Stage 5 paired usability trial dataset (n=12)
│   └── charts/                # Generated publication figures (fig1–fig4)
├── templates/
│   ├── base.html              # App shell, 72px mini rail, budget modal, AI drawer, toasts
│   ├── index.html             # Dashboard: Safe-to-Spend hero, Bento grid, spending pace
│   ├── log_expense.html       # 5-sec Rapid Logger with customizable presets & categories
│   ├── transactions.html      # Transaction ledger with live search, filters, and inline edit
│   ├── calendar.html          # Interactive spending calendar & daily wallet mood check-ins
│   ├── splits_bills.html      # Shared roommate splits, settlements, and recurring bills
│   └── cooldown.html          # 48-Hour Impulse Cooldown tank with countdown timers
├── static/
│   ├── css/
│   │   └── style.css          # Editorial fintech theme (Sage green, warm stone, hairline borders)
│   └── js/
│       ├── app.js             # Client engine: Rapid logger, mini rail, Chart.js, voice/AI drawer
│       ├── calendar.js        # Spending calendar interactive grid & day detail drawer
│       └── telemetry.js       # Interaction metrics & task duration tracking
└── tests/
    └── test_backend.py        # 20 automated unit tests for routes, models, and AI engine
```

---

## Quick Setup & Installation

### Prerequisites
- Python 3.10 or higher
- Git
- Google AI Studio API Key (optional for Gemini AI features; offline mode works without a key)

### 1. Clone the Repository
```bash
git clone <repository_url>
cd "expence traker"
```

### 2. Create and Activate a Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate    # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to create `.env`:
```bash
cp .env.example .env
```

Open `.env` and add your Google Gemini API key:
```env
GEMINI_API_KEY=your_actual_google_ai_studio_key_here
FLASK_SECRET_KEY=smartspend_secure_session_key_2026
```

> **Note:** If `GEMINI_API_KEY` is omitted or offline, SmartSpend gracefully activates its built-in rule-based parsing engine, ensuring live demos and core features never crash.

### 5. Launch the Web Application
```bash
python app.py
```
Open your browser and navigate to: **`http://localhost:5000`**

---

## Core Features & Functionality

### 1. Calm "Safe-to-Spend Today" Dashboard (`/`)
- **Pacing Formula:**
  $$\text{Safe-to-Spend Today} = \max\left(0, \frac{B_{\text{remaining}}}{D_{\text{remaining}}}\right) = \max\left(0, \frac{B_{\text{monthly}} - S_{\text{month}}}{D_{\text{remaining}}}\right)$$
- Visual feedback in soothing Forest Green (`#10B981`) when on pace.
- Overspending transitions gently to Warm Amber (`#F59E0B`) with the **Gentle Recovery Coach** suggesting a realistic multi-day adjustment (e.g. *"Trimming ₹15/day for 3 days returns you to your target"*). **Zero red panic alerts.**
- Real-time logging streak counter (e.g. `4d streak`) celebrating daily mindfulness.

### 2. 5-Second Rapid Logger (`/log-expense`)
- **Hostel Presets:** One-tap presets (`Chai ₹20`, `Auto ₹50`, `Tiffin ₹80`, `Snacks ₹100`) prefill amount, category, and intent.
- **Customizable Presets Strip:** Edit amounts, names, and categories directly in the UI.
- **Emotional Intent Tagging:** Categorize spends by feeling (`Essential`, `Craving`, `Friends`, `Impulse`).
- **1-Tap Friend Split:** Enter total bill, toggle split, select participant count (2, 3, 4+), and only your share is debited from your daily safe-to-spend.

### 3. 1-Button Voice Assistant & Multimodal Voice Logging
- **Voice Tap Button:** Record audio directly from the browser microphone (`AudioRecorder` API).
- **Multimodal AI Extraction:** Audio is sent to `gemini-2.5-flash` to extract structured JSON with amount, category, merchant name, date, and split count.
- **Client Speech Fallback:** Native Web Speech recognition fallback for instant local transcription.

### 4. SmartSpend AI Assistant Drawer
- Powered by `gemini-2.5-flash` through the official `google-genai` Python SDK (`genai.Client`).
- **Chat-to-Log:** Natural commands like *"Spent 120 on lunch at campus mess"* create transactions in one step.
- **Context-Aware Inquiries:** Ask *"Can I afford dinner out with friends?"* and SmartSpend AI references your real-time balance and safe-to-spend limit before advising.
- **Interactive Action Badges:** Quick prompts for logging, balance queries, split calculations, and saving tips.

### 5. Collapsible 72px Icon-Only Mini Rail & Mobile Drawer
- **Desktop (`>= 1024px`):** Smoothly transitions between a full `240px` sidebar and an icon-only `72px` rail. Navigation icons center in sleek pills with floating dark tooltips (`data-tooltip`).
- **Mobile (`< 1024px`):** Off-canvas slide-out drawer (`260px`) with a dimmed backdrop overlay and bottom tab navigation.
- **Keyboard Shortcuts:** `Ctrl + B` / `Cmd + B` toggles the sidebar; `Escape` closes mobile drawers and modals.
- **State Persistence:** Preserves collapsed state in `localStorage` with an anti-flicker early check.

### 6. Interactive Spending Calendar (`/calendar`)
- Day-by-day heatmap intensity grid tracking spending against daily budget benchmarks.
- Daily wallet mood check-ins (`Calm`, `Confident`, `Cautious`, `Regretful`).
- Inspect past day breakdowns or log past expenses with date preservation.

### 7. Hostel Splits & Recurring Bills (`/splits-bills`)
- Split group dinners, grocery runs, and auto rides with roommates.
- Track pending settlements with visual badges.
- Manage monthly recurring expenses (WiFi, laundry, rent).

### 8. 48-Hour Impulse Cooldown Tank (`/cooldown`)
- Park online shopping desires for 48 hours to prevent impulse buys.
- Live countdown timers ticking down the cooling period.
- Clicking **"Skipped It!"** increments the *"Total Impulse Money Saved"* counter.

### 9. CSV Ledger Export (`/api/export/expenses`)
- One-click clean CSV export of your entire transaction history.

---

## Design System & Aesthetics

SmartSpend adheres to a strict, cohesive **Warm Editorial Fintech** design language:

| Token | Hex Value | Usage |
| :--- | :--- | :--- |
| **Forest Green** | `#1B4332` | Primary brand color, hero cards, active accents |
| **Sage Tint** | `#EAF2EE` | Subtle background highlights, badges, active tabs |
| **Warm Stone** | `#F5F5F0` | Main application background surface |
| **Sidebar Surface** | `#EFEFE9` | Navigation panel surface |
| **Charcoal Ink** | `#18181B` | Primary typography and headings |
| **Muted Ink** | `#71717A` | Secondary labels, captions, metadata |
| **Hairline Border** | `#E4E4DC` | Crisp borders and component dividers |
| **Card Surface** | `#FFFFFF` | Bento grid cards, modal surfaces |

- **Typography:** Inter (`wght@400;500;600;700;800`) with tabular numbers (`tnum`) for monetary figures.
- **Iconography:** Lucide monochrome SVG icons (zero OS Unicode emoji glyphs).
- **Accessibility:** High contrast ratios complying with WCAG 2.1 AA standards.

---

## Statistical Validation & Empirical Results

SmartSpend was developed alongside an academic empirical validation suite located in `analysis/validate_stats.py`:

```bash
python analysis/validate_stats.py
```

### 1. Problem Validation Survey ($n = 35$)
- **Correlation:** Strong statistically significant correlation ($r = 0.8360, p < 0.001$) between forgotten transactions and student financial anxiety.
- **Satisfaction Baseline:** One-sample t-test ($t(34) = -2.03, p = 0.025$) confirmed students are significantly dissatisfied with manual or UPI transaction tracking.

### 2. Paired Usability Trial ($n = 12$)
- **Efficiency:** Average expense logging time dropped from **75.96s** (traditional forms) to **23.62s** (SmartSpend Rapid Logger), a **68.9% reduction in friction** ($t(11) = -13.59, p < 0.0001$).
- **Effect Size:** Cohen's $d = 3.923$ (exceptionally large positive effect, $d \gg 0.8$).
- **System Usability Scale (SUS):** Mean score of **94.2 / 100** (Grade A, Top 10% usability), significantly outperforming the industry 68.0 benchmark ($p < 0.0001$).

Figures generated in `analysis/charts/`:
- `fig1_baseline_survey_distribution.png`: Budget distributions, correlation scatter, and satisfaction boxplots.
- `fig2_time_efficiency_paired.png`: Paired time slopegraph and group boxplots.
- `fig3_sus_score_distribution.png`: SUS score distribution against the 68.0 industry benchmark.
- `fig4_satisfaction_comparison.png`: User satisfaction comparison with 95% confidence intervals.

---

## Automated Test Suite

SmartSpend includes comprehensive unit and integration tests covering database helpers, calculations, routes, and AI handling:

```bash
python -m unittest tests/test_backend.py -v
```

All 20 backend unit tests validate:
- SQLite schema generation and user initialization
- Safe-to-Spend pacing and recovery formulas
- Consecutive day logging streak calculations
- Category management and customizable presets
- 48-Hour Impulse Cooldown lifecycle
- Shared splits and settlements
- AI JSON extraction and fallback parsing
- Route status codes and mini-rail markup integrity

---

## Tech Stack & Credits

- **Backend:** [Flask](https://flask.palletsprojects.com/) (Python 3.10+)
- **AI SDK:** [google-genai](https://pypi.org/project/google-genai/) by Google DeepMind / Google Cloud
- **Database:** [SQLite3](https://www.sqlite.org/) (lightweight, zero-config embedded SQL)
- **Data Science:** [NumPy](https://numpy.org/), [Pandas](https://pandas.pydata.org/), [SciPy](https://scipy.org/), [Matplotlib](https://matplotlib.org/)
- **Frontend:** Vanilla JavaScript (ES6+), HTML5, CSS3 Custom Properties
- **Charts:** [Chart.js](https://www.chartjs.org/) (v4.4 via CDN)
- **Icons:** [Lucide](https://lucide.dev/) monochrome SVG icons
- **Typography:** [Inter](https://fonts.google.com/specimen/Inter) by Rasmus Andersson via Google Fonts

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
