# SmartSpend: AI-Powered Personal Budget Tracker

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.x-green.svg)](https://flask.palletsprojects.com/)
[![Google Gemini API](https://img.shields.io/badge/Google%20GenAI-gemini--2.5--flash-orange.svg)](https://ai.google.dev/)
[![SQLite](https://img.shields.io/badge/Database-SQLite3-lightgrey.svg)](https://www.sqlite.org/)
[![Design System](https://img.shields.io/badge/Design-Editorial%20Fintech-1B4332.svg)](#design-system--aesthetics)

A simple web-based personal expense tracker built for college hostel and PG students to log daily expenses quickly and stay within their monthly budget.

## Features

- **Quick Expense Logging:** Add daily expenses in seconds using presets and categories.
- **Voice & Natural Language Input:** Speak or type expenses naturally (e.g., *"20 rs for chai"*, *"split 240 pizza with Raj and Amit"*) to automatically fill in the amount, category, and split details.
- **AI Budget Assistant:** Uses Google Gemini (`gemini-2.5-flash`) for expense parsing and budget Q&A. Automatically switches to an offline rule-based parser if no API key is set.
- **Daily Safe-to-Spend:** Calculates how much you can spend per day based on your remaining monthly budget.
- **Spending Calendar & Transactions:** View daily spending on a calendar, search or filter past entries, edit records, and export data to CSV.
- **Splits & Bills:** Track shared roommate expenses, settlements, and monthly bills.
- **48-Hour Wishlist:** Hold impulse purchases for 48 hours before deciding whether to buy them.

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

## Tech Stack & Credits

- **Backend:** [Flask](https://flask.palletsprojects.com/) (Python 3.10+)
- **AI SDK:** [google-genai](https://pypi.org/project/google-genai/) by Google DeepMind / Google Cloud
- **Database:** [SQLite3](https://www.sqlite.org/) (lightweight, zero-config embedded SQL)
- **Data Science:** [NumPy](https://numpy.org/), [Pandas](https://pandas.pydata.org/), [SciPy](https://scipy.org/), [Matplotlib](https://matplotlib.org/)
- **Frontend:** Vanilla JavaScript (ES6+), HTML5, CSS3 Custom Properties
- **Charts:** [Chart.js](https://www.chartjs.org/) (v4.4 via CDN)
- **Icons:** [Lucide](https://lucide.dev/) monochrome SVG icons
- **Typography:** [Inter](https://fonts.google.com/specimen/Inter) by Rasmus Andersson via Google Fonts

