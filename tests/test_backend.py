"""test_backend.py - Unit & Integration Test Suite for SpendCalm Backend and Math Engine."""

import datetime
import json
import os
import re
import sqlite3
import tempfile
import unittest

# Import spendcalm modules
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import ai_helper
import app as flask_app
import models


class SpendCalmModelTests(unittest.TestCase):
    """Test SQLite models, financial calculations, constraints, and helpers."""

    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        models.init_db(self.db_path)

    def tearDown(self):
        os.close(self.db_fd)
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_user_creation_and_retrieval(self):
        user = models.get_or_create_user("P99", 3500.0, db_path=self.db_path)
        self.assertEqual(user["participant_code"], "P99")
        self.assertEqual(user["monthly_budget"], 3500.0)

        # Re-fetching returns the exact same user
        same_user = models.get_or_create_user("P99", 3000.0, db_path=self.db_path)
        self.assertEqual(same_user["id"], user["id"])

        # Invalid budget rejection
        with self.assertRaises(ValueError):
            models.get_or_create_user("P98", -500, db_path=self.db_path)

    def test_expense_logging_and_validation(self):
        user = models.get_or_create_user("P01", 3000.0, db_path=self.db_path)

        # Valid single expense
        exp_id = models.add_expense(
            user_id=user["id"],
            amount=20.0,
            category="Food",
            mood_tag="Essential",
            is_split=False,
            split_count=1,
            note="Morning Chai",
            db_path=self.db_path,
        )
        self.assertIsInstance(exp_id, int)

        # Valid split expense (₹300 split 3 ways = ₹100 share)
        split_id = models.add_expense(
            user_id=user["id"],
            amount=300.0,
            category="Food",
            mood_tag="Friends",
            is_split=True,
            split_count=3,
            split_with="Raj & Amit",
            note="Pizza treat",
            db_path=self.db_path,
        )
        expenses = models.get_expenses(user["id"], db_path=self.db_path)
        self.assertEqual(len(expenses), 2)
        # Verify split amount stored is 100.0
        pizza_exp = next(e for e in expenses if e["id"] == split_id)
        self.assertEqual(pizza_exp["amount"], 100.0)
        self.assertEqual(pizza_exp["is_split"], 1)
        self.assertEqual(pizza_exp["split_count"], 3)
        self.assertEqual(pizza_exp["owed_amount"], 200.0)
        self.assertEqual(pizza_exp["split_with"], "Raj & Amit")

        # Invalid category rejection
        with self.assertRaises(ValueError):
            models.add_expense(user["id"], 50.0, "Crypto", "Essential", db_path=self.db_path)

        # Invalid mood tag rejection
        with self.assertRaises(ValueError):
            models.add_expense(user["id"], 50.0, "Food", "Panic", db_path=self.db_path)

        # Invalid zero/negative amount rejection
        with self.assertRaises(ValueError):
            models.add_expense(user["id"], -10.0, "Food", "Essential", db_path=self.db_path)

    def test_default_categories_and_custom_crud(self):
        """Test category auto-seeding, custom creation, rename with history sync, and safe delete."""
        user = models.get_or_create_user("P10_CAT", 3000.0, db_path=self.db_path)

        # 1. Defaults auto-seeded
        cats = models.get_categories(user["id"], db_path=self.db_path)
        cat_names = [c["name"] for c in cats]
        for expected in ["Food", "Travel", "Hostel/PG", "Fun", "Misc"]:
            self.assertIn(expected, cat_names)

        # 2. Add custom category
        new_cat = models.add_category(user["id"], "Gym", "dumbbell", "#1B4332", db_path=self.db_path)
        self.assertEqual(new_cat["name"], "Gym")
        self.assertEqual(new_cat["icon"], "dumbbell")

        # Duplicate name rejection
        with self.assertRaises(ValueError):
            models.add_category(user["id"], "gym", "dumbbell", "#1B4332", db_path=self.db_path)

        # Name length validation
        with self.assertRaises(ValueError):
            models.add_category(user["id"], "X", "tag", "#6B7280", db_path=self.db_path)
        with self.assertRaises(ValueError):
            models.add_category(user["id"], "A" * 25, "tag", "#6B7280", db_path=self.db_path)

        # 3. Log expense & bill with custom category
        exp_id = models.add_expense(
            user_id=user["id"],
            amount=500.0,
            category="Gym",
            mood_tag="Essential",
            note="Monthly gym membership",
            db_path=self.db_path
        )
        bill = models.add_recurring_bill(
            user_id=user["id"],
            title="Gym Membership",
            amount=500.0,
            category="Gym",
            db_path=self.db_path
        )

        # 4. Rename category -> verifies historical update on expenses & bills
        updated = models.update_category(new_cat["id"], user["id"], "Fitness", "dumbbell", "#4A6FA5", db_path=self.db_path)
        self.assertEqual(updated["name"], "Fitness")

        # Check expense updated
        exp = models.get_expense_by_id(exp_id, db_path=self.db_path)
        self.assertEqual(exp["category"], "Fitness")

        # Check bill updated
        bills = models.get_recurring_bills(user["id"], db_path=self.db_path)
        gym_bill = next(b for b in bills if b["id"] == bill["id"])
        self.assertEqual(gym_bill["category"], "Fitness")

        # 5. Delete category -> safe fallback to Misc
        models.delete_category(new_cat["id"], user["id"], db_path=self.db_path)
        exp_after_delete = models.get_expense_by_id(exp_id, db_path=self.db_path)
        self.assertEqual(exp_after_delete["category"], "Misc")

        # 6. Cannot delete Misc
        misc_cat = next(c for c in models.get_categories(user["id"], db_path=self.db_path) if c["name"] == "Misc")
        with self.assertRaises(ValueError):
            models.delete_category(misc_cat["id"], user["id"], db_path=self.db_path)

    def test_safe_to_spend_math_and_gentle_recovery(self):
        user = models.get_or_create_user("P02", 3000.0, db_path=self.db_path)
        # Target test date: Nov 21, 2026 (10 days remaining in November)
        test_date = datetime.date(2026, 11, 21)

        # Before any spending:
        metrics = models.calculate_safe_to_spend(user["id"], target_date=test_date, db_path=self.db_path)
        # 3000 / 10 = 300.00
        self.assertEqual(metrics["days_remaining"], 10)
        self.assertEqual(metrics["safe_to_spend_today"], 300.00)
        self.assertEqual(metrics["status_tone"], "safe")
        self.assertIn("cruising smoothly", metrics["coach_message"])

        # Log ₹50 spend today (within 80% of daily allowance)
        models.add_expense(
            user_id=user["id"],
            amount=50.0,
            category="Food",
            mood_tag="Essential",
            created_at="2026-11-21 10:00:00",
            db_path=self.db_path,
        )
        metrics2 = models.calculate_safe_to_spend(user["id"], target_date=test_date, db_path=self.db_path)
        self.assertEqual(metrics2["spent_today"], 50.00)
        self.assertEqual(metrics2["safe_to_spend_today"], 250.00)
        self.assertEqual(metrics2["status_tone"], "safe")

        # Overspend today: log ₹350 more today (total today = ₹400 > ₹300 allowance)
        models.add_expense(
            user_id=user["id"],
            amount=350.0,
            category="Fun",
            mood_tag="Impulse",
            created_at="2026-11-21 14:00:00",
            db_path=self.db_path,
        )
        metrics3 = models.calculate_safe_to_spend(user["id"], target_date=test_date, db_path=self.db_path)
        self.assertEqual(metrics3["status_tone"], "caution")
        self.assertEqual(metrics3["safe_to_spend_today"], 0.0)
        self.assertIn("A little over today—no stress", metrics3["coach_message"])
        self.assertIn("Trimming ₹", metrics3["coach_message"])

    def test_unified_safe_to_spend_math_consistency(self):
        """Verify Bug 1 fix: safe_to_spend_today is identical across hero and coach logic."""
        user = models.get_or_create_user("P02_UNIFY", 3000.0, db_path=self.db_path)
        test_date = datetime.date(2026, 11, 21)

        # Prior spend in month (e.g. ₹500 on Nov 10)
        models.add_expense(
            user_id=user["id"],
            amount=500.0,
            category="Food",
            mood_tag="Essential",
            created_at="2026-11-10 12:00:00",
            db_path=self.db_path,
        )

        # Spent today: ₹100
        models.add_expense(
            user_id=user["id"],
            amount=100.0,
            category="Food",
            mood_tag="Essential",
            created_at="2026-11-21 09:00:00",
            db_path=self.db_path,
        )

        metrics = models.calculate_safe_to_spend(user["id"], target_date=test_date, db_path=self.db_path)
        # days_remaining = 10
        # spent_before_today = 500
        # daily_target = round((3000 - 500) / 10, 2) = 250.00
        # safe_to_spend_today = max(0, 250 - 100) = 150.00
        self.assertEqual(metrics["daily_target"], 250.00)
        self.assertEqual(metrics["safe_to_spend_today"], 150.00)
        self.assertIn("150.00", metrics["coach_message"])

    def test_streak_calculation(self):
        user = models.get_or_create_user("P03", 3000.0, db_path=self.db_path)
        test_date = datetime.date(2026, 11, 21)

        # No expenses -> streak 0
        streak0 = models.calculate_streak(user["id"], target_date=test_date, db_path=self.db_path)
        self.assertEqual(streak0, 0)

        # Log expense yesterday (Nov 20) and today (Nov 21) -> streak 2
        models.add_expense(user["id"], 20.0, "Food", "Essential", created_at="2026-11-20 09:00:00", db_path=self.db_path)
        models.add_expense(user["id"], 20.0, "Food", "Essential", created_at="2026-11-21 09:00:00", db_path=self.db_path)
        streak2 = models.calculate_streak(user["id"], target_date=test_date, db_path=self.db_path)
        self.assertEqual(streak2, 2)

    def test_calendar_data(self):
        user = models.get_or_create_user("P04", 3000.0, db_path=self.db_path)
        cal_data = models.get_monthly_calendar_data(user["id"], 2026, 11, db_path=self.db_path)
        self.assertEqual(cal_data["year"], 2026)
        self.assertEqual(cal_data["month"], 11)
        self.assertIn("days", cal_data)
        self.assertIn("summary", cal_data)

    def test_cooldown_wishlist_lifecycle(self):
        user = models.get_or_create_user("P04", 3000.0, db_path=self.db_path)

        # Add item
        item = models.add_cooldown_item(user["id"], "Gaming Mouse", 899.0, db_path=self.db_path)
        self.assertEqual(item["item_name"], "Gaming Mouse")
        self.assertEqual(item["status"], "waiting")

        # Mark skipped -> increases total saved
        res = models.update_cooldown_item(item["id"], user["id"], "skipped", db_path=self.db_path)
        self.assertEqual(res["total_saved"], 899.0)

        # Add another item and mark bought -> automatically logs an expense
        item2 = models.add_cooldown_item(user["id"], "Graphic Tee", 499.0, db_path=self.db_path)
        res2 = models.update_cooldown_item(item2["id"], user["id"], "bought", db_path=self.db_path)
        self.assertIsNotNone(res2["expense_id"])

        expenses = models.get_expenses(user["id"], db_path=self.db_path)
        self.assertTrue(any("Graphic Tee" in e["note"] for e in expenses))

    def test_undo_delete_and_update_expense(self):
        user = models.get_or_create_user("P05_UNDO", 3000.0, db_path=self.db_path)
        exp_id = models.add_expense(
            user_id=user["id"],
            amount=50.0,
            category="Food",
            mood_tag="Essential",
            note="Mess Snacks",
            db_path=self.db_path,
        )

        # Update expense
        updated = models.update_expense(
            expense_id=exp_id,
            user_id=user["id"],
            amount=60.0,
            category="Food",
            mood_tag="Craving",
            note="Evening Samosa",
            db_path=self.db_path,
        )
        self.assertTrue(updated)
        exp = models.get_expense_by_id(exp_id, db_path=self.db_path)
        self.assertEqual(exp["amount"], 60.0)
        self.assertEqual(exp["mood_tag"], "Craving")

        # Delete expense (backed up for 5-sec undo)
        deleted = models.delete_expense(exp_id, user_id=user["id"], db_path=self.db_path)
        self.assertTrue(deleted)
        self.assertIsNone(models.get_expense_by_id(exp_id, db_path=self.db_path))

        # Restore expense
        restored = models.restore_expense(exp_id, user["id"], db_path=self.db_path)
        self.assertTrue(restored)
        restored_exp = models.get_expense_by_id(exp_id, db_path=self.db_path)
        self.assertIsNotNone(restored_exp)
        self.assertEqual(restored_exp["amount"], 60.0)


class SpendCalmFlaskAPITests(unittest.TestCase):
    """Test Flask routes, REST APIs, CSV exports, and telemetry endpoints."""

    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        models.init_db(self.db_path)
        # Patch models DB path to temp DB
        models.DB_NAME = self.db_path
        flask_app.app.config["TESTING"] = True
        self.client = flask_app.app.test_client()

    def tearDown(self):
        os.close(self.db_fd)
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_html_pages_render(self):
        routes = ["/", "/log-expense", "/transactions", "/splits-bills", "/cooldown", "/calendar"]
        for r in routes:
            resp = self.client.get(r)
            self.assertEqual(resp.status_code, 200, f"Route {r} failed with status {resp.status_code}")
            self.assertIn(b"SmartSpend", resp.data)

        # Test clean 302 redirects for legacy /insights, /test-mode, and /feedback
        self.assertEqual(self.client.get("/insights").status_code, 302)
        self.assertEqual(self.client.get("/test-mode").status_code, 302)
        self.assertEqual(self.client.get("/feedback").status_code, 302)

    def test_session_api(self):
        resp = self.client.post("/api/session", json={"participant_code": "P10", "monthly_budget": 2800.0})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["user"]["participant_code"], "P10")
        self.assertEqual(data["user"]["monthly_budget"], 2800.0)

    def test_rapid_expense_api(self):
        # Setup session
        self.client.post("/api/session", json={"participant_code": "P11", "monthly_budget": 3000.0})

        # Log expense
        resp = self.client.post(
            "/api/expenses",
            json={
                "amount": 20.0,
                "category": "Food",
                "mood_tag": "Essential",
                "is_split": False,
                "split_count": 1,
                "note": "Morning Chai",
            },
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertEqual(data["logged_amount"], 20.0)

        # Check dashboard
        dash_resp = self.client.get("/api/dashboard")
        self.assertEqual(dash_resp.status_code, 200)
        dash_data = dash_resp.get_json()
        self.assertEqual(len(dash_data["expenses"]), 1)

    def test_crud_expense_and_undo_api(self):
        self.client.post("/api/session", json={"participant_code": "P12_CRUD", "monthly_budget": 3000.0})

        # Create
        post_resp = self.client.post(
            "/api/expenses",
            json={
                "amount": 100.0,
                "category": "Food",
                "mood_tag": "Craving",
                "note": "Night Pizza",
            },
        )
        self.assertEqual(post_resp.status_code, 201)
        exp_id = post_resp.get_json()["expense_id"]

        # Edit (PUT)
        put_resp = self.client.put(
            f"/api/expenses/{exp_id}",
            json={
                "amount": 80.0,
                "category": "Food",
                "mood_tag": "Essential",
                "note": "Regular Pizza",
            },
        )
        self.assertEqual(put_resp.status_code, 200)

        # Delete (DELETE)
        del_resp = self.client.delete(f"/api/expenses/{exp_id}")
        self.assertEqual(del_resp.status_code, 200)

        # Restore (5-Sec Undo)
        restore_resp = self.client.post("/api/expenses/restore", json={"expense_id": exp_id})
        self.assertEqual(restore_resp.status_code, 200)

    def test_splits_and_recurring_bills_api(self):
        self.client.post("/api/session", json={"participant_code": "P13_SPLITS", "monthly_budget": 3000.0})

        # Create a split expense
        resp = self.client.post(
            "/api/expenses",
            json={
                "amount": 300.0,
                "category": "Food",
                "mood_tag": "Friends",
                "is_split": True,
                "split_count": 3,
                "split_with": "Raj & Amit",
                "note": "Dinner treat",
            },
        )
        self.assertEqual(resp.status_code, 201)
        exp_id = resp.get_json()["expense_id"]

        # Fetch splits-bills
        sb_resp = self.client.get("/api/splits-bills")
        self.assertEqual(sb_resp.status_code, 200)
        sb_data = sb_resp.get_json()
        self.assertEqual(sb_data["pending_total"], 200.0)
        self.assertEqual(len(sb_data["pending_splits"]), 1)

        # Settle split
        settle_resp = self.client.post(f"/api/expenses/{exp_id}/settle")
        self.assertEqual(settle_resp.status_code, 200)
        sb_data_after = self.client.get("/api/splits-bills").get_json()
        self.assertEqual(sb_data_after["pending_total"], 0.0)
        self.assertEqual(len(sb_data_after["settled_splits"]), 1)

        # Add recurring bill
        rec_resp = self.client.post("/api/recurring", json={"title": "Hostel Wi-Fi", "amount": 350.0, "category": "Hostel/PG"})
        self.assertEqual(rec_resp.status_code, 201)
        bill_id = rec_resp.get_json()["bill"]["id"]

        # 1-Tap Log bill for this month
        log_rec_resp = self.client.post(f"/api/recurring/{bill_id}/log")
        self.assertEqual(log_rec_resp.status_code, 201)

        # Delete recurring bill
        del_rec_resp = self.client.delete(f"/api/recurring/{bill_id}")
        self.assertEqual(del_rec_resp.status_code, 200)

    def test_insights_api(self):
        self.client.post("/api/session", json={"participant_code": "P14_INSIGHTS", "monthly_budget": 3000.0})
        # Log a couple expenses
        self.client.post("/api/expenses", json={"amount": 40.0, "category": "Food", "mood_tag": "Essential", "note": "Lunch"})
        self.client.post("/api/expenses", json={"amount": 60.0, "category": "Travel", "mood_tag": "Craving", "note": "Cab"})

        resp = self.client.get("/api/insights")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("daily_average_spend", data)
        self.assertIn("essential_vs_non_essential", data)
        self.assertIn("highest_spend_day", data)
        self.assertIn("category_breakdown", data)
        self.assertIn("intent_breakdown", data)
        self.assertIn("seven_day_trend", data)
        self.assertIn("safe_daily_reference", data)
        self.assertIn("stories", data)

    def test_category_crud_api(self):
        """Test Category REST APIs: GET, POST, PUT, DELETE, and safety constraints."""
        self.client.post("/api/session", json={"participant_code": "P25_CAT", "monthly_budget": 3000.0})

        # 1. GET /api/categories
        resp = self.client.get("/api/categories")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "ok")
        cat_names = [c["name"] for c in data["categories"]]
        self.assertIn("Food", cat_names)
        self.assertIn("Misc", cat_names)

        # 2. POST /api/categories
        create_resp = self.client.post(
            "/api/categories",
            json={"name": "Laundry", "icon": "shirt", "color": "#4A6FA5"}
        )
        self.assertEqual(create_resp.status_code, 201)
        cat_data = create_resp.get_json()["category"]
        cat_id = cat_data["id"]
        self.assertEqual(cat_data["name"], "Laundry")

        # Duplicate rejection
        dup_resp = self.client.post("/api/categories", json={"name": "Laundry"})
        self.assertEqual(dup_resp.status_code, 400)

        # 3. PUT /api/categories/<id>
        update_resp = self.client.put(
            f"/api/categories/{cat_id}",
            json={"name": "Wash & Fold", "icon": "shirt", "color": "#1B4332"}
        )
        self.assertEqual(update_resp.status_code, 200)
        updated_data = update_resp.get_json()["category"]
        self.assertEqual(updated_data["name"], "Wash & Fold")

        # 4. DELETE /api/categories/<id>
        del_resp = self.client.delete(f"/api/categories/{cat_id}")
        self.assertEqual(del_resp.status_code, 200)
        self.assertEqual(del_resp.get_json()["status"], "deleted")

        # Attempt to delete Misc -> 400
        misc_id = next(c["id"] for c in data["categories"] if c["name"] == "Misc")
        del_misc_resp = self.client.delete(f"/api/categories/{misc_id}")
        self.assertEqual(del_misc_resp.status_code, 400)

    def test_budget_update_api(self):
        # Test updating budget without specifying participant code
        resp = self.client.post("/api/session", json={"monthly_budget": 3500.0})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["user"]["monthly_budget"], 3500.0)

    def test_csv_exports(self):
        # Test expenses export succeeds
        resp = self.client.get("/api/export/expenses")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.mimetype, "text/csv")
        self.assertIn("smartspend_expenses.csv", resp.headers.get("Content-Disposition", ""))

        # Test removed export types return 400
        for invalid_type in ["telemetry", "sus", "random"]:
            bad_resp = self.client.get(f"/api/export/{invalid_type}")
            self.assertEqual(bad_resp.status_code, 400)

    def test_ai_chat_resilience_and_clean_notes(self):
        """Verify Bug 3 fix: AI extracts 2-3 word memory anchors, not raw commands."""
        self.client.post("/api/session", json={"participant_code": "P20", "monthly_budget": 3000.0})

        # Test offline fallback parser clean note extraction
        clean_note_1 = ai_helper.sanitize_note("Log 30 Rs In Chai With Friends", "Food")
        self.assertNotIn("Log", clean_note_1)
        self.assertNotIn("30", clean_note_1)

        clean_note_2 = ai_helper.sanitize_note("Add 50 for auto to metro", "Travel")
        self.assertNotIn("Add", clean_note_2)
        self.assertNotIn("50", clean_note_2)

        # Test advice query
        resp = self.client.post("/api/ai-chat", json={"message": "can i afford a treat today?"})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["mode"], "advice")
        self.assertIn("safe to spend today", data["reply"].lower())

        # Test chat-to-log query
        resp2 = self.client.post("/api/ai-chat", json={"message": "spent 60 on auto to college"})
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.get_json()
        self.assertEqual(data2["mode"], "log_expense")
        self.assertIsNotNone(data2["expense_logged"])
        self.assertEqual(data2["expense_logged"]["category"], "Travel")
        self.assertNotIn("spent 60", data2["expense_logged"]["note"].lower())

    def test_zero_os_emojis_in_templates_and_static(self):
        """Strict verification: zero Unicode emojis across templates, CSS, and JS."""
        # Unicode emoji regex ranges
        emoji_pattern = re.compile(
            "[\U00010000-\U0010ffff]|"
            "[\u2600-\u27BF]|"
            "[\u2300-\u23FF]|"
            "[\u2B50-\u2B55]|"
            "[\u203C-\u2049]"
        )

        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        check_dirs = [
            os.path.join(base_dir, "templates"),
            os.path.join(base_dir, "static", "css"),
            os.path.join(base_dir, "static", "js"),
        ]

        for d in check_dirs:
            for root, _, files in os.walk(d):
                for f in files:
                    if f.endswith((".html", ".css", ".js")):
                        fpath = os.path.join(root, f)
                        with open(fpath, "r", encoding="utf-8") as file_obj:
                            content = file_obj.read()
                            matches = emoji_pattern.findall(content)
                            self.assertEqual(
                                len(matches),
                                0,
                                f"Found OS emojis in {f}: {matches[:5]}"
                            )


if __name__ == "__main__":
    unittest.main()
