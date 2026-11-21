"""models.py - SQLite Schema, Database Helpers, and Financial Logic for SmartSpend.

Handles:
- Auto-initialization and non-destructive PRAGMA table_info migrations
- Anonymized user session & budget management
- Rapid expense logging with category, mood tagging, split tracking, and custom dates
- Edit & 5-Second Undo Delete functionality
- 48-Hour Impulse Cooldown wishlist
- Hostel Splits & Fixed/Recurring Bills management
- Unified Safe-to-Spend Today, streak counter, and dynamic Gentle Recovery Coach math
- Statistical insights & 7-day spending trends
- Telemetry & System Usability Scale (SUS) survey persistence
"""

import calendar
import datetime
import math
import os
import re
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

DB_NAME = "database.db"

ALLOWED_CATEGORIES = {'Food', 'Travel', 'Hostel/PG', 'Fun', 'Misc'}
ALLOWED_MOOD_TAGS = {'Essential', 'Craving', 'Friends', 'Impulse'}

DEFAULT_CATEGORIES = [
    {"name": "Food", "icon": "utensils", "color": "#1B4332", "is_default": 1},
    {"name": "Travel", "icon": "car", "color": "#4A6FA5", "is_default": 1},
    {"name": "Hostel/PG", "icon": "home", "color": "#C9A66B", "is_default": 1},
    {"name": "Fun", "icon": "gamepad-2", "color": "#C06C52", "is_default": 1},
    {"name": "Misc", "icon": "more-horizontal", "color": "#6B7280", "is_default": 1},
]

CATEGORY_COLORS = {
    'Food': '#1B4332',       # Deep Forest
    'Travel': '#4A6FA5',     # Slate Blue
    'Hostel/PG': '#C9A66B',  # Warm Sand
    'Fun': '#C06C52',        # Muted Terracotta
    'Misc': '#6B7280'        # Neutral Slate
}

MOOD_COLORS = {
    'Essential': '#1B4332',
    'Craving': '#D97706',
    'Friends': '#4A6FA5',
    'Impulse': '#C06C52'
}


def get_db_path(custom_path: Optional[str] = None) -> str:
    """Return the absolute path to the SQLite database file."""
    if custom_path:
        return custom_path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, DB_NAME)


def get_db(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Open and return a SQLite connection configured with Row factory and foreign keys."""
    path = get_db_path(db_path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """Initialize database schema with required tables, indexes, and non-destructive migrations."""
    conn = get_db(db_path)
    cursor = conn.cursor()

    cursor.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            participant_code TEXT UNIQUE NOT NULL,
            monthly_budget REAL NOT NULL DEFAULT 3000.0 CHECK (monthly_budget > 0),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            icon TEXT NOT NULL DEFAULT 'tag',
            color TEXT NOT NULL DEFAULT '#6B7280',
            is_default INTEGER NOT NULL DEFAULT 0,
            UNIQUE(user_id, name),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL CHECK (amount > 0),
            category TEXT NOT NULL,
            mood_tag TEXT NOT NULL CHECK (mood_tag IN ('Essential', 'Craving', 'Friends', 'Impulse')),
            is_split INTEGER NOT NULL DEFAULT 0 CHECK (is_split IN (0, 1)),
            split_count INTEGER NOT NULL DEFAULT 1 CHECK (split_count >= 1),
            owed_amount REAL DEFAULT 0.0,
            split_settled INTEGER DEFAULT 0,
            split_with TEXT DEFAULT '',
            expense_date TEXT,
            note TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS deleted_expenses (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            mood_tag TEXT NOT NULL,
            is_split INTEGER NOT NULL DEFAULT 0,
            split_count INTEGER NOT NULL DEFAULT 1,
            owed_amount REAL DEFAULT 0.0,
            split_settled INTEGER DEFAULT 0,
            split_with TEXT DEFAULT '',
            expense_date TEXT,
            note TEXT DEFAULT '',
            created_at TIMESTAMP,
            deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS recurring_bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            amount REAL NOT NULL CHECK (amount > 0),
            category TEXT NOT NULL,
            last_logged_month TEXT DEFAULT '',
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

        CREATE TABLE IF NOT EXISTS mood_checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            checkin_date TEXT NOT NULL,
            mood TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, checkin_date),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_expenses_user_date ON expenses(user_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_categories_user ON categories(user_id);
        CREATE INDEX IF NOT EXISTS idx_mood_checkins_user_date ON mood_checkins(user_id, checkin_date);
        """
    )
    conn.commit()

    # Non-destructive migrations for existing SQLite databases
    cursor.execute("PRAGMA table_info(expenses)")
    existing_cols = {row["name"] for row in cursor.fetchall()}

    if "owed_amount" not in existing_cols:
        cursor.execute("ALTER TABLE expenses ADD COLUMN owed_amount REAL DEFAULT 0.0")
    if "split_settled" not in existing_cols:
        cursor.execute("ALTER TABLE expenses ADD COLUMN split_settled INTEGER DEFAULT 0")
    if "split_with" not in existing_cols:
        cursor.execute("ALTER TABLE expenses ADD COLUMN split_with TEXT DEFAULT ''")
    if "expense_date" not in existing_cols:
        cursor.execute("ALTER TABLE expenses ADD COLUMN expense_date TEXT")
        cursor.execute("UPDATE expenses SET expense_date = date(created_at) WHERE expense_date IS NULL OR expense_date = ''")

    # Migrate expenses table to remove CHECK (category IN ...) constraint if present
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='expenses'")
    row_exp = cursor.fetchone()
    if row_exp and "category IN" in row_exp["sql"]:
        cursor.execute("PRAGMA foreign_keys = OFF;")
        cursor.execute("""
            CREATE TABLE expenses_unconstrained (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL CHECK (amount > 0),
                category TEXT NOT NULL,
                mood_tag TEXT NOT NULL CHECK (mood_tag IN ('Essential', 'Craving', 'Friends', 'Impulse')),
                is_split INTEGER NOT NULL DEFAULT 0 CHECK (is_split IN (0, 1)),
                split_count INTEGER NOT NULL DEFAULT 1 CHECK (split_count >= 1),
                owed_amount REAL DEFAULT 0.0,
                split_settled INTEGER DEFAULT 0,
                split_with TEXT DEFAULT '',
                expense_date TEXT,
                note TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)
        cursor.execute("""
            INSERT INTO expenses_unconstrained (id, user_id, amount, category, mood_tag, is_split, split_count, owed_amount, split_settled, split_with, expense_date, note, created_at)
            SELECT id, user_id, amount, category, mood_tag, is_split, split_count,
                   COALESCE(owed_amount, 0.0), COALESCE(split_settled, 0), COALESCE(split_with, ''),
                   COALESCE(expense_date, date(created_at)), COALESCE(note, ''), created_at
            FROM expenses;
        """)
        cursor.execute("DROP TABLE expenses;")
        cursor.execute("ALTER TABLE expenses_unconstrained RENAME TO expenses;")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_expenses_user_date ON expenses(user_id, created_at);")
        cursor.execute("PRAGMA foreign_keys = ON;")

    # Migrate recurring_bills table to remove CHECK (category IN ...) constraint if present
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='recurring_bills'")
    row_rb = cursor.fetchone()
    if row_rb and "category IN" in row_rb["sql"]:
        cursor.execute("PRAGMA foreign_keys = OFF;")
        cursor.execute("""
            CREATE TABLE recurring_bills_unconstrained (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                amount REAL NOT NULL CHECK (amount > 0),
                category TEXT NOT NULL,
                last_logged_month TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)
        cursor.execute("""
            INSERT INTO recurring_bills_unconstrained (id, user_id, title, amount, category, last_logged_month, created_at)
            SELECT id, user_id, title, amount, category, last_logged_month, created_at
            FROM recurring_bills;
        """)
        cursor.execute("DROP TABLE recurring_bills;")
        cursor.execute("ALTER TABLE recurring_bills_unconstrained RENAME TO recurring_bills;")
        cursor.execute("PRAGMA foreign_keys = ON;")

    conn.commit()
    conn.close()


# -------------------------------------------------------------------------
# Dynamic Categories System (CRUD + Defaults)
# -------------------------------------------------------------------------

def seed_default_categories(user_id: int, db_path: Optional[str] = None) -> None:
    """Seed the 5 default categories for a user if they have no categories."""
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM categories WHERE user_id = ?", (user_id,))
    count = cursor.fetchone()["cnt"]
    if count == 0:
        for cat in DEFAULT_CATEGORIES:
            cursor.execute(
                """
                INSERT OR IGNORE INTO categories (user_id, name, icon, color, is_default)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, cat["name"], cat["icon"], cat["color"], cat["is_default"])
            )
        conn.commit()
    conn.close()


def get_categories(user_id: int, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch all categories for a user, auto-seeding defaults if empty."""
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM categories WHERE user_id = ? ORDER BY is_default DESC, id ASC",
        (user_id,)
    )
    rows = cursor.fetchall()
    if not rows:
        conn.close()
        seed_default_categories(user_id, db_path)
        conn = get_db(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM categories WHERE user_id = ? ORDER BY is_default DESC, id ASC",
            (user_id,)
        )
        rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_category_names(user_id: int, db_path: Optional[str] = None) -> set:
    """Return set of valid category names for this user."""
    cats = get_categories(user_id, db_path)
    names = {c["name"] for c in cats}
    names.update(ALLOWED_CATEGORIES)
    return names


def add_category(
    user_id: int,
    name: str,
    icon: str = "tag",
    color: str = "#6B7280",
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new custom category for a user."""
    clean_name = (name or "").strip()
    if len(clean_name) < 2 or len(clean_name) > 20:
        raise ValueError("Category name must be between 2 and 20 characters.")

    clean_icon = re.sub(r"[^a-zA-Z0-9\-]", "", (icon or "tag").strip())[:30] or "tag"
    clean_color = (color or "#6B7280").strip()
    if not re.match(r"^#[0-9a-fA-F]{6}$", clean_color):
        clean_color = "#6B7280"

    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM categories WHERE user_id = ? AND LOWER(name) = LOWER(?)",
        (user_id, clean_name)
    )
    if cursor.fetchone():
        conn.close()
        raise ValueError(f"Category '{clean_name}' already exists.")

    cursor.execute(
        """
        INSERT INTO categories (user_id, name, icon, color, is_default)
        VALUES (?, ?, ?, ?, 0)
        """,
        (user_id, clean_name, clean_icon, clean_color)
    )
    conn.commit()
    cat_id = cursor.lastrowid
    cursor.execute("SELECT * FROM categories WHERE id = ?", (cat_id,))
    new_cat = dict(cursor.fetchone())
    conn.close()
    return new_cat


def update_category(
    cat_id: int,
    user_id: int,
    name: str,
    icon: str,
    color: str,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """Rename category or change its icon/color; updates historical expenses & bills."""
    clean_name = (name or "").strip()
    if len(clean_name) < 2 or len(clean_name) > 20:
        raise ValueError("Category name must be between 2 and 20 characters.")

    clean_icon = re.sub(r"[^a-zA-Z0-9\-]", "", (icon or "tag").strip())[:30] or "tag"
    clean_color = (color or "#6B7280").strip()
    if not re.match(r"^#[0-9a-fA-F]{6}$", clean_color):
        clean_color = "#6B7280"

    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM categories WHERE id = ? AND user_id = ?", (cat_id, user_id))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        raise ValueError("Category not found.")

    old_name = existing["name"]

    if old_name.lower() != clean_name.lower():
        cursor.execute(
            "SELECT id FROM categories WHERE user_id = ? AND LOWER(name) = LOWER(?) AND id != ?",
            (user_id, clean_name, cat_id)
        )
        if cursor.fetchone():
            conn.close()
            raise ValueError(f"Category '{clean_name}' already exists.")

    cursor.execute(
        """
        UPDATE categories
        SET name = ?, icon = ?, color = ?
        WHERE id = ? AND user_id = ?
        """,
        (clean_name, clean_icon, clean_color, cat_id, user_id)
    )

    if old_name != clean_name:
        cursor.execute(
            "UPDATE expenses SET category = ? WHERE user_id = ? AND category = ?",
            (clean_name, user_id, old_name)
        )
        cursor.execute(
            "UPDATE recurring_bills SET category = ? WHERE user_id = ? AND category = ?",
            (clean_name, user_id, old_name)
        )

    conn.commit()
    cursor.execute("SELECT * FROM categories WHERE id = ?", (cat_id,))
    updated_cat = dict(cursor.fetchone())
    conn.close()
    return updated_cat


def delete_category(
    cat_id: int,
    user_id: int,
    db_path: Optional[str] = None
) -> bool:
    """Delete a custom category; safely reassigns existing expenses and bills to 'Misc'."""
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM categories WHERE id = ? AND user_id = ?", (cat_id, user_id))
    cat = cursor.fetchone()
    if not cat:
        conn.close()
        return False

    cat_name = cat["name"]
    if cat_name.lower() == "misc":
        conn.close()
        raise ValueError("Default category 'Misc' cannot be deleted.")

    # Reassign expenses and recurring bills to 'Misc'
    cursor.execute(
        "UPDATE expenses SET category = 'Misc' WHERE user_id = ? AND category = ?",
        (user_id, cat_name)
    )
    cursor.execute(
        "UPDATE recurring_bills SET category = 'Misc' WHERE user_id = ? AND category = ?",
        (user_id, cat_name)
    )

    cursor.execute("DELETE FROM categories WHERE id = ? AND user_id = ?", (cat_id, user_id))
    conn.commit()
    conn.close()
    return True


# -------------------------------------------------------------------------
# User & Session Helpers
# -------------------------------------------------------------------------

def get_or_create_user(participant_code: str, monthly_budget: float = 3000.0, db_path: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve existing user by participant code, or create a new anonymized record."""
    code = participant_code.strip().upper()
    if not code:
        raise ValueError("Participant code cannot be empty.")
    budget = float(monthly_budget)
    if budget <= 0:
        raise ValueError("Monthly budget must be greater than zero.")

    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE participant_code = ?", (code,))
    row = cursor.fetchone()

    if row:
        user_data = dict(row)
        conn.close()
        seed_default_categories(user_data["id"], db_path)
        return user_data

    cursor.execute(
        "INSERT INTO users (participant_code, monthly_budget) VALUES (?, ?)",
        (code, budget),
    )
    conn.commit()
    new_id = cursor.lastrowid
    cursor.execute("SELECT * FROM users WHERE id = ?", (new_id,))
    user_data = dict(cursor.fetchone())
    conn.close()
    seed_default_categories(new_id, db_path)
    return user_data


def update_user_budget(user_id: int, new_budget: float, db_path: Optional[str] = None) -> bool:
    """Update monthly budget for a participant."""
    if new_budget <= 0:
        raise ValueError("Budget must be greater than zero.")
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET monthly_budget = ? WHERE id = ?", (float(new_budget), user_id))
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    return rows_affected > 0


def get_user_by_id(user_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Fetch user dictionary by user ID."""
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


# -------------------------------------------------------------------------
# Expense Management (CRUD + Splits + 5-Sec Undo)
# -------------------------------------------------------------------------

def add_expense(
    user_id: int,
    amount: float,
    category: str,
    mood_tag: str,
    is_split: bool = False,
    split_count: int = 1,
    note: str = "",
    expense_date: Optional[str] = None,
    split_with: str = "",
    owed_amount: Optional[float] = None,
    created_at: Optional[str] = None,
    db_path: Optional[str] = None,
) -> int:
    """Insert a new expense into SQLite and return its new primary key ID.

    If is_split is True and split_count > 1, the user's logged amount is
    amount / split_count, and friends' owed share is amount - (amount / split_count).
    """
    raw_amount = float(amount)
    if raw_amount <= 0:
        raise ValueError("Amount must be greater than zero.")

    valid_categories = get_category_names(user_id, db_path)
    if category not in valid_categories:
        raise ValueError(f"Category '{category}' is invalid. Allowed: {sorted(list(valid_categories))}")

    if mood_tag not in ALLOWED_MOOD_TAGS:
        raise ValueError(f"Mood tag '{mood_tag}' is invalid. Allowed: {ALLOWED_MOOD_TAGS}")

    split_int = int(split_count) if is_split else 1
    if split_int < 1:
        split_int = 1

    if is_split and split_int > 1:
        final_amount = round(raw_amount / split_int, 2)
        calc_owed = round(raw_amount - final_amount, 2) if owed_amount is None else float(owed_amount)
    else:
        final_amount = raw_amount
        calc_owed = 0.0

    split_flag = 1 if is_split else 0
    clean_note = (note or "").strip()[:60]
    clean_split_with = (split_with or "").strip()[:100]

    now = datetime.datetime.now()
    if expense_date:
        exp_date_str = expense_date.strip()
    elif created_at:
        exp_date_str = str(created_at)[:10]
    else:
        exp_date_str = now.strftime("%Y-%m-%d")

    timestamp = created_at or f"{exp_date_str} {now.strftime('%H:%M:%S')}"

    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO expenses (
            user_id, amount, category, mood_tag, is_split, split_count,
            owed_amount, split_settled, split_with, expense_date, note, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)
        """,
        (
            user_id, final_amount, category, mood_tag, split_flag, split_int,
            calc_owed, clean_split_with, exp_date_str, clean_note, timestamp
        ),
    )
    conn.commit()
    expense_id = cursor.lastrowid
    conn.close()
    return expense_id


def update_expense(
    expense_id: int,
    user_id: int,
    amount: float,
    category: str,
    mood_tag: str,
    note: str = "",
    expense_date: Optional[str] = None,
    is_split: bool = False,
    split_count: int = 1,
    split_with: str = "",
    db_path: Optional[str] = None,
) -> bool:
    """Update an existing expense record."""
    raw_amount = float(amount)
    if raw_amount <= 0:
        raise ValueError("Amount must be greater than zero.")

    valid_categories = get_category_names(user_id, db_path)
    if category not in valid_categories:
        raise ValueError(f"Category '{category}' is invalid. Allowed: {sorted(list(valid_categories))}")

    if mood_tag not in ALLOWED_MOOD_TAGS:
        raise ValueError(f"Mood tag '{mood_tag}' is invalid.")

    split_int = int(split_count) if is_split else 1
    if split_int < 1:
        split_int = 1

    if is_split and split_int > 1:
        final_amount = round(raw_amount / split_int, 2)
        calc_owed = round(raw_amount - final_amount, 2)
    else:
        final_amount = raw_amount
        calc_owed = 0.0

    split_flag = 1 if is_split else 0
    clean_note = (note or "").strip()[:60]
    clean_split_with = (split_with or "").strip()[:100]

    conn = get_db(db_path)
    cursor = conn.cursor()

    if expense_date:
        cursor.execute(
            """
            UPDATE expenses
            SET amount = ?, category = ?, mood_tag = ?, is_split = ?, split_count = ?,
                owed_amount = ?, split_with = ?, expense_date = ?, note = ?
            WHERE id = ? AND user_id = ?
            """,
            (
                final_amount, category, mood_tag, split_flag, split_int,
                calc_owed, clean_split_with, expense_date.strip(), clean_note,
                expense_id, user_id
            ),
        )
    else:
        cursor.execute(
            """
            UPDATE expenses
            SET amount = ?, category = ?, mood_tag = ?, is_split = ?, split_count = ?,
                owed_amount = ?, split_with = ?, note = ?
            WHERE id = ? AND user_id = ?
            """,
            (
                final_amount, category, mood_tag, split_flag, split_int,
                calc_owed, clean_split_with, clean_note,
                expense_id, user_id
            ),
        )

    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def delete_expense(expense_id: int, user_id: Optional[int] = None, db_path: Optional[str] = None) -> bool:
    """Delete an expense by ID, backing it up into deleted_expenses for 5-sec undo."""
    conn = get_db(db_path)
    cursor = conn.cursor()

    if user_id is not None:
        cursor.execute("SELECT * FROM expenses WHERE id = ? AND user_id = ?", (expense_id, user_id))
    else:
        cursor.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,))

    row = cursor.fetchone()
    if not row:
        conn.close()
        return False

    # Back up into deleted_expenses
    cursor.execute(
        """
        INSERT OR REPLACE INTO deleted_expenses (
            id, user_id, amount, category, mood_tag, is_split, split_count,
            owed_amount, split_settled, split_with, expense_date, note, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row["id"], row["user_id"], row["amount"], row["category"], row["mood_tag"],
            row["is_split"], row["split_count"], row["owed_amount"] if "owed_amount" in row.keys() else 0.0,
            row["split_settled"] if "split_settled" in row.keys() else 0,
            row["split_with"] if "split_with" in row.keys() else "",
            row["expense_date"] if "expense_date" in row.keys() else str(row["created_at"])[:10],
            row["note"], row["created_at"]
        ),
    )

    if user_id is not None:
        cursor.execute("DELETE FROM expenses WHERE id = ? AND user_id = ?", (expense_id, user_id))
    else:
        cursor.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))

    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def restore_expense(expense_id: int, user_id: int, db_path: Optional[str] = None) -> bool:
    """Restore a deleted expense from the deleted_expenses backup table (5-Sec Undo)."""
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM deleted_expenses WHERE id = ? AND user_id = ?", (expense_id, user_id))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False

    cursor.execute(
        """
        INSERT OR REPLACE INTO expenses (
            id, user_id, amount, category, mood_tag, is_split, split_count,
            owed_amount, split_settled, split_with, expense_date, note, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row["id"], row["user_id"], row["amount"], row["category"], row["mood_tag"],
            row["is_split"], row["split_count"], row["owed_amount"], row["split_settled"],
            row["split_with"], row["expense_date"], row["note"], row["created_at"]
        ),
    )
    cursor.execute("DELETE FROM deleted_expenses WHERE id = ?", (expense_id,))
    conn.commit()
    conn.close()
    return True


def get_expenses(
    user_id: int,
    category: Optional[str] = None,
    mood_tag: Optional[str] = None,
    search: Optional[str] = None,
    date_range: Optional[str] = None,  # today, 7days, month, all
    limit: int = 100,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieve expense history with filters, live search, and date ranges."""
    conn = get_db(db_path)
    cursor = conn.cursor()

    query = "SELECT * FROM expenses WHERE user_id = ?"
    params: List[Any] = [user_id]

    valid_cats = get_category_names(user_id, db_path)
    if category and category in valid_cats:
        query += " AND category = ?"
        params.append(category)

    if mood_tag and mood_tag in ALLOWED_MOOD_TAGS:
        query += " AND mood_tag = ?"
        params.append(mood_tag)

    if search:
        query += " AND (note LIKE ? OR category LIKE ? OR split_with LIKE ?)"
        term = f"%{search.strip()}%"
        params.extend([term, term, term])

    today = datetime.date.today()
    if date_range == "today":
        query += " AND (expense_date = ? OR date(created_at) = ?)"
        today_str = today.strftime("%Y-%m-%d")
        params.extend([today_str, today_str])
    elif date_range == "7days":
        start_7d = (today - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
        query += " AND (COALESCE(expense_date, date(created_at)) >= ?)"
        params.append(start_7d)
    elif date_range == "month":
        month_str = today.strftime("%Y-%m")
        query += " AND (strftime('%Y-%m', COALESCE(expense_date, created_at)) = ?)"
        params.append(month_str)

    query += " ORDER BY COALESCE(expense_date, date(created_at)) DESC, created_at DESC, id DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_expense_by_id(expense_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve a single expense record by primary key ID."""
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


# -------------------------------------------------------------------------
# Safe-to-Spend & Gentle Recovery Math (Unified Source of Truth)
# -------------------------------------------------------------------------

def calculate_safe_to_spend(user_id: int, target_date: Optional[datetime.date] = None, db_path: Optional[str] = None) -> Dict[str, Any]:
    """Calculate the Calm Safe-to-Spend Today metrics and Gentle Recovery Coach feedback.

    Unified Formula:
    days_remaining = max(1, (days_in_month - today.day) + 1)
    daily_target = round((monthly_budget - spent_before_today) / days_remaining, 2)
    safe_to_spend_today = round(max(0.0, daily_target - spent_today), 2)

    Both the hero card and coaching banner display this exact same figure.
    """
    conn = get_db(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        raise ValueError(f"User {user_id} not found.")

    budget = float(user["monthly_budget"])
    today = target_date or datetime.date.today()
    month_prefix = today.strftime("%Y-%m")
    today_str = today.strftime("%Y-%m-%d")

    # Total days in current month & days remaining
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    days_remaining = max(1, (days_in_month - today.day) + 1)

    # Fetch expenses in current calendar month
    cursor.execute(
        """
        SELECT id, amount, category, mood_tag, is_split, split_count, note, created_at,
               COALESCE(expense_date, date(created_at)) as exp_date
        FROM expenses
        WHERE user_id = ? AND strftime('%Y-%m', COALESCE(expense_date, created_at)) = ?
        ORDER BY created_at DESC
        """,
        (user_id, month_prefix),
    )
    month_expenses = cursor.fetchall()
    conn.close()

    total_spent_month = 0.0
    spent_today = 0.0
    user_cats = get_categories(user_id, db_path=db_path)
    category_totals = {c["name"]: 0.0 for c in user_cats}
    for def_cat in ['Food', 'Travel', 'Hostel/PG', 'Fun', 'Misc']:
        if def_cat not in category_totals:
            category_totals[def_cat] = 0.0
    mood_totals = {m: 0.0 for m in ['Essential', 'Craving', 'Friends', 'Impulse']}

    for exp in month_expenses:
        amt = float(exp["amount"])
        total_spent_month += amt
        if exp["exp_date"] == today_str:
            spent_today += amt
        cat_key = exp["category"]
        if cat_key not in category_totals:
            category_totals[cat_key] = 0.0
        category_totals[cat_key] += amt
        if exp["mood_tag"] in mood_totals:
            mood_totals[exp["mood_tag"]] += amt

    total_spent_month = round(total_spent_month, 2)
    spent_today = round(spent_today, 2)
    category_totals = {k: round(v, 2) for k, v in category_totals.items()}
    mood_totals = {k: round(v, 2) for k, v in mood_totals.items()}

    # UNIFIED MATH (Single Source of Truth)
    spent_before_today = max(0.0, total_spent_month - spent_today)
    daily_target = round(max(0.0, (budget - spent_before_today) / days_remaining), 2)
    safe_to_spend_today = round(max(0.0, daily_target - spent_today), 2)

    # Status tone & Gentle Recovery Coach messaging
    status_tone = "safe"  # safe | nearing | caution
    coach_message = ""

    if total_spent_month >= budget:
        status_tone = "caution"
        coach_message = "Monthly budget reached—take it easy and focus on essentials for the remaining days."
    elif safe_to_spend_today <= 0.0:
        status_tone = "caution"
        excess = spent_today - daily_target
        recovery_window = min(4, max(1, days_remaining - 1))
        daily_trim = math.ceil(excess / recovery_window) if recovery_window > 0 else math.ceil(excess)
        coach_message = (
            f"A little over today—no stress. Trimming ₹{int(daily_trim)}/day for the next "
            f"{recovery_window} day{'s' if recovery_window > 1 else ''} gets you right back on track."
        )
    elif spent_today > (0.8 * daily_target):
        status_tone = "nearing"
        coach_message = f"Almost at today's calm limit—₹{safe_to_spend_today:.2f} left for tonight."
    else:
        status_tone = "safe"
        coach_message = f"You're cruising smoothly! ₹{safe_to_spend_today:.2f} is comfortably safe for the rest of today."

    percent_used = min(100.0, round((total_spent_month / budget) * 100, 1)) if budget > 0 else 0.0

    # Auto Story Insight
    if total_spent_month == 0:
        story_insight = "Welcome to SmartSpend! Log your first spend or tap a preset to establish your daily rhythm."
    else:
        non_essentials = {k: v for k, v in mood_totals.items() if k != "Essential" and v > 0}
        if non_essentials:
            top_mood = max(non_essentials.items(), key=lambda x: x[1])
            pct_mood = round((top_mood[1] / total_spent_month) * 100)
            story_insight = f"Heads up: '{top_mood[0]}' spends totaled ₹{top_mood[1]:.0f} this month—{pct_mood}% of your total spends."
        else:
            story_insight = "Great job: 100% of your expenses this month have gone toward essentials!"

    streak = calculate_streak(user_id, target_date=today, db_path=db_path)

    # Top spending category
    active_cats = {k: v for k, v in category_totals.items() if v > 0}
    top_cat = max(active_cats.items(), key=lambda x: x[1])[0] if active_cats else "None"

    return {
        "monthly_budget": budget,
        "total_spent_month": total_spent_month,
        "spent_today": spent_today,
        "days_remaining": days_remaining,
        "daily_target": daily_target,
        "safe_to_spend_today": safe_to_spend_today,
        "remaining_today": safe_to_spend_today,  # identical for backward-compatibility
        "percent_used": percent_used,
        "status_tone": status_tone,
        "coach_message": coach_message,
        "story_insight": story_insight,
        "category_totals": category_totals,
        "mood_totals": mood_totals,
        "top_category": top_cat,
        "streak": streak,
    }


def calculate_streak(user_id: int, target_date: Optional[datetime.date] = None, db_path: Optional[str] = None) -> int:
    """Calculate the consecutive day logging streak ending today (or yesterday)."""
    today = target_date or datetime.date.today()
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT DISTINCT COALESCE(expense_date, date(created_at)) as log_date
        FROM expenses
        WHERE user_id = ?
        ORDER BY log_date DESC
        """,
        (user_id,),
    )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return 0

    log_dates = {datetime.datetime.strptime(r["log_date"], "%Y-%m-%d").date() for r in rows if r["log_date"]}

    current = today
    if current not in log_dates:
        yesterday = today - datetime.timedelta(days=1)
        if yesterday in log_dates:
            current = yesterday
        else:
            return 0

    streak = 0
    while current in log_dates:
        streak += 1
        current -= datetime.timedelta(days=1)

    return streak


# -------------------------------------------------------------------------
# Insights & Visual Analytics Data Generator
# -------------------------------------------------------------------------

def get_insights_data(user_id: int, target_date: Optional[datetime.date] = None, db_path: Optional[str] = None) -> Dict[str, Any]:
    """Compile comprehensive analytics for the /insights section."""
    today = target_date or datetime.date.today()
    month_prefix = today.strftime("%Y-%m")
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    current_day = today.day

    metrics = calculate_safe_to_spend(user_id, target_date=today, db_path=db_path)
    budget = metrics["monthly_budget"]
    total_spent = metrics["total_spent_month"]

    # 1. Daily Average Spend
    daily_avg = round(total_spent / max(1, current_day), 2)

    # 2. Essential vs. Non-Essential Ratio
    essential_spent = metrics["mood_totals"].get("Essential", 0.0)
    non_essential_spent = max(0.0, total_spent - essential_spent)
    essential_pct = round((essential_spent / total_spent) * 100, 1) if total_spent > 0 else 100.0
    non_essential_pct = round(100.0 - essential_pct, 1)

    # 3. Highest Spend Day
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT COALESCE(expense_date, date(created_at)) as day_date, SUM(amount) as day_total
        FROM expenses
        WHERE user_id = ? AND strftime('%Y-%m', COALESCE(expense_date, created_at)) = ?
        GROUP BY day_date
        ORDER BY day_total DESC LIMIT 1
        """,
        (user_id, month_prefix),
    )
    highest_row = cursor.fetchone()
    highest_day = {
        "date": highest_row["day_date"] if highest_row else "None",
        "amount": round(float(highest_row["day_total"]), 2) if highest_row else 0.0
    }

    # 4. Itemized Category Breakdown
    user_cats = get_categories(user_id, db_path=db_path)
    cat_meta = {c["name"]: {"color": c["color"], "icon": c.get("icon", "tag")} for c in user_cats}
    cat_breakdown = []
    for cat, amt in metrics["category_totals"].items():
        pct = round((amt / total_spent) * 100, 1) if total_spent > 0 else 0.0
        color = cat_meta.get(cat, {}).get("color", CATEGORY_COLORS.get(cat, "#6B7280"))
        icon = cat_meta.get(cat, {}).get("icon", "tag")
        cat_breakdown.append({
            "category": cat,
            "amount": amt,
            "percentage": pct,
            "color": color,
            "icon": icon
        })
    cat_breakdown.sort(key=lambda x: x["amount"], reverse=True)

    # 5. Itemized Intent Breakdown
    intent_breakdown = []
    for mood, amt in metrics["mood_totals"].items():
        pct = round((amt / total_spent) * 100, 1) if total_spent > 0 else 0.0
        intent_breakdown.append({
            "intent": mood,
            "amount": amt,
            "percentage": pct,
            "color": MOOD_COLORS.get(mood, "#6B7280")
        })
    intent_breakdown.sort(key=lambda x: x["amount"], reverse=True)

    # 6. 7-Day Daily Trend
    trend_labels = []
    trend_values = []
    for i in range(6, -1, -1):
        d = today - datetime.timedelta(days=i)
        d_str = d.strftime("%Y-%m-%d")
        cursor.execute(
            """
            SELECT COALESCE(SUM(amount), 0.0) as sum_amt
            FROM expenses
            WHERE user_id = ? AND (expense_date = ? OR (expense_date IS NULL AND date(created_at) = ?))
            """,
            (user_id, d_str, d_str),
        )
        amt_day = float(cursor.fetchone()["sum_amt"])
        trend_labels.append(d.strftime("%a (%d)"))
        trend_values.append(round(amt_day, 2))

    # Safe daily baseline reference
    safe_daily_reference = round(budget / days_in_month, 2)

    # 7. Habit Stories
    stories = []
    if total_spent == 0:
        stories.append("No transactions logged yet this month. Tap a preset to begin!")
    else:
        # Non-essential note
        if non_essential_spent > 0:
            top_mood = max(
                [(m, a) for m, a in metrics["mood_totals"].items() if m != "Essential"],
                key=lambda x: x[1]
            )
            pct_top = round((top_mood[1] / total_spent) * 100)
            stories.append(f"Non-essential spends make up {non_essential_pct}% of your budget this month, led by '{top_mood[0]}' at ₹{top_mood[1]:.0f} ({pct_top}%).")
        else:
            stories.append("Remarkable discipline: 100% of your expenses so far have gone strictly toward essentials.")

        # Weekday vs Weekend spending
        cursor.execute(
            """
            SELECT strftime('%w', COALESCE(expense_date, created_at)) as dow, SUM(amount) as amt, COUNT(DISTINCT COALESCE(expense_date, date(created_at))) as cnt
            FROM expenses
            WHERE user_id = ? AND strftime('%Y-%m', COALESCE(expense_date, created_at)) = ?
            GROUP BY (dow IN ('0', '6'))
            """,
            (user_id, month_prefix),
        )
        dow_rows = cursor.fetchall()
        if len(dow_rows) > 0:
            stories.append(f"Your daily burn rate is ₹{daily_avg:.2f}/day across {current_day} active days in this month cycle.")

    conn.close()

    return {
        "daily_average_spend": daily_avg,
        "essential_ratio": essential_pct,
        "non_essential_ratio": non_essential_pct,
        "essential_vs_non_essential": {
            "essential_pct": essential_pct,
            "non_essential_pct": non_essential_pct,
            "essential_spent": essential_spent,
            "non_essential_spent": non_essential_spent,
        },
        "highest_spend_day": highest_day,
        "category_breakdown": cat_breakdown,
        "intent_breakdown": intent_breakdown,
        "seven_day_trend": {
            "labels": trend_labels,
            "values": trend_values,
        },
        "safe_daily_reference": safe_daily_reference,
        "stories": stories,
        "habit_stories": stories,
        "metrics": metrics,
    }


# -------------------------------------------------------------------------
# Splits & Bills Management
# -------------------------------------------------------------------------

def get_unsettled_splits(user_id: int, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch unsettled friend splits where owed_amount > 0 and split_settled = 0."""
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM expenses
        WHERE user_id = ? AND owed_amount > 0 AND split_settled = 0
        ORDER BY created_at DESC
        """,
        (user_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_settled_splits(user_id: int, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch settled split history."""
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM expenses
        WHERE user_id = ? AND owed_amount > 0 AND split_settled = 1
        ORDER BY created_at DESC LIMIT 30
        """,
        (user_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_pending_splits_total(user_id: int, db_path: Optional[str] = None) -> float:
    """Calculate the total rupee amount friends currently owe the participant."""
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT COALESCE(SUM(owed_amount), 0.0) as total_owed
        FROM expenses
        WHERE user_id = ? AND owed_amount > 0 AND split_settled = 0
        """,
        (user_id,),
    )
    row = cursor.fetchone()
    conn.close()
    return round(float(row["total_owed"]), 2) if row else 0.0


def settle_split(expense_id: int, user_id: int, db_path: Optional[str] = None) -> bool:
    """Mark a friend split as settled."""
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE expenses SET split_settled = 1 WHERE id = ? AND user_id = ?",
        (expense_id, user_id),
    )
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


# Fixed / Recurring Bills
def add_recurring_bill(user_id: int, title: str, amount: float, category: str, db_path: Optional[str] = None) -> Dict[str, Any]:
    """Add a fixed monthly template bill (e.g., PG Rent, Mess Fee, Wi-Fi)."""
    clean_title = (title or "").strip()[:80]
    if not clean_title:
        raise ValueError("Bill title cannot be empty.")
    raw_amount = float(amount)
    if raw_amount <= 0:
        raise ValueError("Amount must be greater than zero.")
    valid_categories = get_category_names(user_id, db_path)
    if category not in valid_categories:
        category = "Hostel/PG"

    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO recurring_bills (user_id, title, amount, category)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, clean_title, raw_amount, category),
    )
    conn.commit()
    bill_id = cursor.lastrowid
    cursor.execute("SELECT * FROM recurring_bills WHERE id = ?", (bill_id,))
    item = dict(cursor.fetchone())
    conn.close()
    return item


def get_recurring_bills(user_id: int, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve recurring bill templates for a user."""
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM recurring_bills WHERE user_id = ? ORDER BY id ASC",
        (user_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_recurring_bill(bill_id: int, user_id: int, db_path: Optional[str] = None) -> bool:
    """Delete a recurring bill template."""
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM recurring_bills WHERE id = ? AND user_id = ?", (bill_id, user_id))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def log_recurring_bill(bill_id: int, user_id: int, current_month: str, db_path: Optional[str] = None) -> Dict[str, Any]:
    """1-Tap log a recurring bill into expenses for the current month."""
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM recurring_bills WHERE id = ? AND user_id = ?", (bill_id, user_id))
    bill = cursor.fetchone()
    if not bill:
        conn.close()
        raise ValueError("Recurring bill template not found.")

    if bill["last_logged_month"] == current_month:
        conn.close()
        return {"status": "already_logged", "message": f"Already logged for {current_month}"}

    # Log into expenses
    expense_id = add_expense(
        user_id=user_id,
        amount=float(bill["amount"]),
        category=bill["category"],
        mood_tag="Essential",
        is_split=False,
        split_count=1,
        note=f"Fixed Bill: {bill['title']}",
        db_path=db_path,
    )

    # Update last_logged_month
    cursor.execute(
        "UPDATE recurring_bills SET last_logged_month = ? WHERE id = ?",
        (current_month, bill_id),
    )
    conn.commit()
    conn.close()

    return {
        "status": "logged",
        "expense_id": expense_id,
        "last_logged_month": current_month,
    }


# -------------------------------------------------------------------------
# 48-Hour Impulse Cooldown Wishlist
# -------------------------------------------------------------------------

def add_cooldown_item(user_id: int, item_name: str, amount: float, db_path: Optional[str] = None) -> Dict[str, Any]:
    """Add a non-essential impulse purchase to the 48-hour cooldown holding tank."""
    name = item_name.strip()[:100]
    if not name:
        raise ValueError("Item name cannot be empty.")
    raw_amount = float(amount)
    if raw_amount <= 0:
        raise ValueError("Amount must be greater than zero.")

    now = datetime.datetime.now()
    unlock_at = (now + datetime.timedelta(hours=48)).strftime("%Y-%m-%d %H:%M:%S")
    created_at = now.strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO cooldown_items (user_id, item_name, amount, created_at, unlock_at, status)
        VALUES (?, ?, ?, ?, ?, 'waiting')
        """,
        (user_id, name, raw_amount, created_at, unlock_at),
    )
    conn.commit()
    item_id = cursor.lastrowid
    cursor.execute("SELECT * FROM cooldown_items WHERE id = ?", (item_id,))
    item = dict(cursor.fetchone())
    conn.close()
    return item


def update_cooldown_item(item_id: int, user_id: int, action: str, db_path: Optional[str] = None) -> Dict[str, Any]:
    """Resolve a cooldown item ('skipped' or 'bought'). If 'bought', logs an expense."""
    if action not in ("skipped", "bought"):
        raise ValueError("Action must be 'skipped' or 'bought'.")

    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cooldown_items WHERE id = ? AND user_id = ?", (item_id, user_id))
    item = cursor.fetchone()
    if not item:
        conn.close()
        raise ValueError(f"Cooldown item {item_id} not found.")

    cursor.execute(
        "UPDATE cooldown_items SET status = ? WHERE id = ? AND user_id = ?",
        (action, item_id, user_id),
    )
    conn.commit()
    conn.close()

    expense_id = None
    if action == "bought":
        expense_id = add_expense(
            user_id=user_id,
            amount=float(item["amount"]),
            category="Fun",
            mood_tag="Impulse",
            is_split=False,
            split_count=1,
            note=f"Cooldown item: {item['item_name']}",
            db_path=db_path,
        )

    saved_total = get_total_cooldown_saved(user_id, db_path=db_path)
    return {
        "status": "updated",
        "action": action,
        "item_id": item_id,
        "expense_id": expense_id,
        "total_saved": saved_total,
    }


def get_cooldown_items(user_id: int, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve all cooldown items for a user."""
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM cooldown_items
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        (user_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_total_cooldown_saved(user_id: int, db_path: Optional[str] = None) -> float:
    """Calculate the total rupee amount of impulse purchases successfully skipped."""
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT COALESCE(SUM(amount), 0.0) as total_saved
        FROM cooldown_items
        WHERE user_id = ? AND status = 'skipped'
        """,
        (user_id,),
    )
    row = cursor.fetchone()
    conn.close()
    return round(float(row["total_saved"]), 2) if row else 0.0


# -------------------------------------------------------------------------
# Calendar Mood Check-ins
# -------------------------------------------------------------------------

def log_mood_checkin(
    user_id: int,
    checkin_date: str,
    mood: str,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """Store or update user's wallet mood check-in for a specific calendar date."""
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO mood_checkins (user_id, checkin_date, mood)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, checkin_date) DO UPDATE SET mood = excluded.mood
        """,
        (user_id, checkin_date.strip(), mood.strip()),
    )
    conn.commit()
    conn.close()
    return {"status": "saved", "date": checkin_date.strip(), "mood": mood.strip()}


def get_monthly_calendar_data(
    user_id: int,
    year: int,
    month: int,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """Calculate and return day-by-day spending totals and status for a given calendar month."""
    if not (1 <= month <= 12):
        raise ValueError(f"Invalid month {month}. Must be between 1 and 12.")

    conn = get_db(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT monthly_budget FROM users WHERE id = ?", (user_id,))
    user_row = cursor.fetchone()
    if not user_row:
        conn.close()
        raise ValueError(f"User {user_id} not found.")

    monthly_budget = float(user_row["monthly_budget"])

    # Calendar month properties
    first_weekday_mon, days_in_month = calendar.monthrange(year, month)
    # Convert Monday=0..Sunday=6 to Sunday=0..Saturday=6
    first_weekday_sun = (first_weekday_mon + 1) % 7
    month_name = calendar.month_name[month]
    daily_target = round(monthly_budget / days_in_month, 2)
    month_prefix = f"{year:04d}-{month:02d}"

    # Query mood check-ins for this month
    cursor.execute(
        """
        SELECT checkin_date, mood
        FROM mood_checkins
        WHERE user_id = ? AND strftime('%Y-%m', checkin_date) = ?
        """,
        (user_id, month_prefix),
    )
    mood_by_date = {row["checkin_date"]: row["mood"] for row in cursor.fetchall()}

    # Query expenses for this month
    cursor.execute(
        """
        SELECT id, amount, category, mood_tag, note, is_split, split_count, split_with,
               COALESCE(expense_date, date(created_at)) as exp_date, created_at
        FROM expenses
        WHERE user_id = ? AND strftime('%Y-%m', COALESCE(expense_date, created_at)) = ?
        ORDER BY exp_date ASC, created_at ASC
        """,
        (user_id, month_prefix),
    )
    expense_rows = cursor.fetchall()
    conn.close()

    # Initialize all dates in month
    days: Dict[str, Dict[str, Any]] = {}
    for d in range(1, days_in_month + 1):
        date_str = f"{year:04d}-{month:02d}-{d:02d}"
        days[date_str] = {
            "date": date_str,
            "day": d,
            "total": 0.0,
            "count": 0,
            "mood_checkin": mood_by_date.get(date_str, None),
            "expenses": []
        }

    # Populate expenses into days
    for exp in expense_rows:
        date_str = exp["exp_date"]
        if date_str in days:
            amt = round(float(exp["amount"]), 2)
            days[date_str]["total"] = round(days[date_str]["total"] + amt, 2)
            days[date_str]["count"] += 1
            days[date_str]["expenses"].append({
                "id": exp["id"],
                "amount": amt,
                "category": exp["category"],
                "mood_tag": exp["mood_tag"],
                "note": exp["note"] or "",
                "is_split": bool(exp["is_split"]),
                "split_count": exp["split_count"] or 1,
                "split_with": exp["split_with"] or ""
            })

    # Summary calculations
    month_total = round(sum(d["total"] for d in days.values()), 2)
    today = datetime.date.today()

    no_spend_days = 0
    calm_days = 0
    heavy_days = 0

    for d in range(1, days_in_month + 1):
        date_obj = datetime.date(year, month, d)
        date_str = f"{year:04d}-{month:02d}-{d:02d}"
        d_info = days[date_str]
        tot = d_info["total"]
        is_past_or_today = (date_obj <= today)

        if is_past_or_today and tot == 0.0:
            no_spend_days += 1
        elif 0.0 < tot <= daily_target:
            calm_days += 1
        elif tot > daily_target:
            heavy_days += 1

    return {
        "year": year,
        "month": month,
        "month_name": month_name,
        "days_in_month": days_in_month,
        "first_weekday": first_weekday_sun,
        "daily_target": daily_target,
        "summary": {
            "month_total": month_total,
            "no_spend_days": no_spend_days,
            "calm_days": calm_days,
            "heavy_days": heavy_days
        },
        "days": days
    }
