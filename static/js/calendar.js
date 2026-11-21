/**
 * calendar.js - Client-Side Interactive Engine for SpendCalm Monthly Spending Calendar.
 * 
 * Features:
 * - Dynamic month-by-month calendar navigation with real SQLite records
 * - 4-column month summary KPI strip (Total, Calm Days, Heavy Days, No-Spend Days)
 * - 7-column calendar grid with calm emotional color coding (Zero, Calm, Heavy, Today)
 * - Interactive Day Inspector panel with live daily pace totals and wallet mood check-ins
 * - Inline transaction editing (shared modal) and deleting with 5-second undo
 * - Pre-filled '+ Log Expense for Date' linking to /log-expense?date=YYYY-MM-DD
 */

let calYear = new Date().getFullYear();
let calMonth = new Date().getMonth() + 1;
let calSelectedDate = new Date().toISOString().slice(0, 10);
let calDataCache = null;

const CATEGORY_ICONS = {
  "Food": "utensils",
  "Travel": "car",
  "Hostel/PG": "home",
  "Fun": "gamepad-2",
  "Misc": "more-horizontal"
};

async function loadCalendarMonth(year, month) {
  try {
    const res = await fetch(`/api/calendar?year=${year}&month=${month}`);
    if (!res.ok) throw new Error("Failed to load calendar data.");
    calDataCache = await res.json();
    calYear = calDataCache.year;
    calMonth = calDataCache.month;

    renderCalendarHeaderAndKPIs();
    renderCalendarDaysGrid();

    // Verify if selected date is within this month
    const monthPrefix = `${calYear}-${String(calMonth).padStart(2, "0")}`;
    if (!calSelectedDate.startsWith(monthPrefix)) {
      const todayStr = new Date().toISOString().slice(0, 10);
      calSelectedDate = todayStr.startsWith(monthPrefix) ? todayStr : `${monthPrefix}-01`;
    }

    highlightSelectedDateCell(calSelectedDate);
    renderDayInspector(calSelectedDate);
  } catch (err) {
    console.error("Error loading calendar:", err);
    if (typeof showToast === "function") {
      showToast("Could not load calendar data.", "error");
    }
  }
}

function renderCalendarHeaderAndKPIs() {
  if (!calDataCache) return;

  // Month-Year Title
  const titleEl = document.getElementById("calMonthYearTitle");
  if (titleEl) {
    titleEl.textContent = `${calDataCache.month_name} ${calDataCache.year}`;
  }

  // 4-Column KPI Strip
  const monthTotalEl = document.getElementById("calKpiMonthTotal");
  const calmDaysEl = document.getElementById("calKpiCalmDays");
  const heavyDaysEl = document.getElementById("calKpiHeavyDays");
  const noSpendDaysEl = document.getElementById("calKpiNoSpendDays");
  const legendCalmLabel = document.getElementById("legendCalmLabel");

  if (monthTotalEl) monthTotalEl.textContent = `₹${calDataCache.summary.month_total.toFixed(2)}`;
  if (calmDaysEl) calmDaysEl.textContent = calDataCache.summary.calm_days;
  if (heavyDaysEl) heavyDaysEl.textContent = calDataCache.summary.heavy_days;
  if (noSpendDaysEl) noSpendDaysEl.textContent = calDataCache.summary.no_spend_days;
  if (legendCalmLabel) legendCalmLabel.textContent = `Calm (≤ ₹${calDataCache.daily_target.toFixed(2)})`;
}

function renderCalendarDaysGrid() {
  const gridContainer = document.getElementById("calendarGridDays");
  if (!gridContainer || !calDataCache) return;

  const todayStr = new Date().toISOString().slice(0, 10);
  const firstWeekday = calDataCache.first_weekday; // 0=Sun..6=Sat
  const daysInMonth = calDataCache.days_in_month;
  const dailyTarget = calDataCache.daily_target;

  let cellsHtml = "";

  // 1. Leading empty cells
  for (let i = 0; i < firstWeekday; i++) {
    cellsHtml += `<div class="cal-day-cell cell-empty" aria-hidden="true"></div>`;
  }

  // 2. Days in month
  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = `${calYear}-${String(calMonth).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
    const dayData = calDataCache.days[dateStr] || { total: 0, count: 0, mood_checkin: null, expenses: [] };
    const isToday = dateStr === todayStr;
    const isSelected = dateStr === calSelectedDate;
    const isPastOrToday = dateStr <= todayStr;

    // Emotional Color Coding
    let colorClass = "cell-future";
    if (dayData.total > dailyTarget) {
      colorClass = "cell-heavy";
    } else if (dayData.total > 0) {
      colorClass = "cell-calm";
    } else if (isPastOrToday) {
      colorClass = "cell-zero";
    }

    const todayTag = isToday ? `<span class="cell-today-tag">Today</span>` : "";
    const txDot = dayData.count > 0 ? `<span class="cell-tx-dot" title="${dayData.count} spend${dayData.count > 1 ? 's' : ''}"></span>` : "";
    const moodPill = dayData.mood_checkin ? `<span class="cell-mood-pill">${dayData.mood_checkin}</span>` : "";

    let bottomRowContent = "";
    if (dayData.total > 0) {
      bottomRowContent = `<span class="cell-total-amt tnum">₹${Math.round(dayData.total)}</span>`;
    } else if (isPastOrToday) {
      bottomRowContent = `
        <span class="cell-zero-label">
          <i data-lucide="check" style="width: 11px; height: 11px; stroke: var(--brand-forest);"></i>
          <span>Zero</span>
        </span>
      `;
    } else {
      bottomRowContent = `<span class="cell-zero-label" style="opacity: 0.35;">—</span>`;
    }

    cellsHtml += `
      <div class="cal-day-cell ${colorClass} ${isToday ? 'is-today' : ''} ${isSelected ? 'is-selected' : ''}" 
           data-date="${dateStr}" 
           role="gridcell" 
           tabindex="0"
           aria-label="${dateStr}, total spent ₹${dayData.total.toFixed(2)}">
        <div class="cell-top-row">
          <span class="cell-day-num tnum">${d}</span>
          <div class="cell-top-meta">
            ${todayTag}
            ${txDot}
            ${moodPill}
          </div>
        </div>
        <div class="cell-bottom-row">
          ${bottomRowContent}
        </div>
      </div>
    `;
  }

  // 3. Trailing empty cells to round out the 7-column grid
  const totalSlots = firstWeekday + daysInMonth;
  const trailingCount = (7 - (totalSlots % 7)) % 7;
  for (let i = 0; i < trailingCount; i++) {
    cellsHtml += `<div class="cal-day-cell cell-empty" aria-hidden="true"></div>`;
  }

  gridContainer.innerHTML = cellsHtml;

  // Attach click listener to every date cell
  gridContainer.querySelectorAll(".cal-day-cell:not(.cell-empty)").forEach(cell => {
    cell.addEventListener("click", () => {
      const dateStr = cell.getAttribute("data-date");
      calSelectedDate = dateStr;
      highlightSelectedDateCell(dateStr);
      renderDayInspector(dateStr);
    });

    cell.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        cell.click();
      }
    });
  });

  if (window.lucide) {
    window.lucide.createIcons();
  }
}

function highlightSelectedDateCell(dateStr) {
  const gridContainer = document.getElementById("calendarGridDays");
  if (!gridContainer) return;

  gridContainer.querySelectorAll(".cal-day-cell").forEach(cell => {
    if (cell.getAttribute("data-date") === dateStr) {
      cell.classList.add("is-selected");
    } else {
      cell.classList.remove("is-selected");
    }
  });
}

function renderDayInspector(dateStr) {
  if (!calDataCache) return;

  const dayData = calDataCache.days[dateStr] || { total: 0, count: 0, mood_checkin: null, expenses: [] };
  const dailyTarget = calDataCache.daily_target;
  const todayStr = new Date().toISOString().slice(0, 10);
  const isPastOrToday = dateStr <= todayStr;

  // Format Date (e.g. Saturday, Nov 21, 2026)
  const parts = dateStr.split("-");
  const dateObj = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
  const fullDateStr = dateObj.toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric", year: "numeric" });
  const shortDateStr = dateObj.toLocaleDateString("en-US", { month: "short", day: "numeric" });

  const dateTitleEl = document.getElementById("inspectorDateFull");
  const daySubEl = document.getElementById("inspectorDaySub");
  const statusPillEl = document.getElementById("inspectorStatusPill");
  const dayTotalEl = document.getElementById("inspectorDayTotal");
  const dayTargetEl = document.getElementById("inspectorDayTarget");
  const moodContainer = document.getElementById("inspectorMoodContainer");
  const txCountEl = document.getElementById("inspectorTxCount");
  const expensesListEl = document.getElementById("inspectorExpensesList");
  const logBtnText = document.getElementById("inspectorLogBtnText");
  const logBtn = document.getElementById("inspectorLogBtn");

  if (dateTitleEl) dateTitleEl.textContent = fullDateStr;
  if (daySubEl) {
    daySubEl.textContent = dateStr === todayStr ? "Today's Ledger & Pace" : `Date: ${dateStr}`;
  }

  // Status Pill
  if (statusPillEl) {
    if (!isPastOrToday) {
      statusPillEl.className = "cal-status-pill pill-future";
      statusPillEl.textContent = "Future Date";
    } else if (dayData.total === 0) {
      statusPillEl.className = "cal-status-pill pill-zero";
      statusPillEl.textContent = "No-Spend Day";
    } else if (dayData.total <= dailyTarget) {
      statusPillEl.className = "cal-status-pill pill-calm";
      statusPillEl.textContent = "Within Pace";
    } else {
      statusPillEl.className = "cal-status-pill pill-heavy";
      statusPillEl.textContent = "Over Daily Pace";
    }
  }

  // Day Total & Target
  if (dayTotalEl) dayTotalEl.textContent = `₹${dayData.total.toFixed(2)}`;
  if (dayTargetEl) dayTargetEl.textContent = `₹${dailyTarget.toFixed(2)}`;

  // Wallet Mood Check-in Badge & Selector
  if (moodContainer) {
    if (dayData.mood_checkin) {
      moodContainer.innerHTML = `
        <span class="activity-pill" style="background-color: var(--brand-sage-bg); color: var(--brand-forest); font-weight: 700; padding: 3px 8px; font-size: 0.75rem;">
          ${dayData.mood_checkin}
        </span>
        <button type="button" class="btn-cal-action change-mood-btn" title="Change wallet mood" aria-label="Change wallet mood">
          <i data-lucide="edit-2" style="width: 12px; height: 12px; stroke: var(--ink-secondary);"></i>
        </button>
      `;
    } else {
      moodContainer.innerHTML = `
        <button type="button" class="preset-chip-btn add-mood-btn" style="padding: 3px 10px; font-size: 0.6875rem;">
          + Check-in Mood
        </button>
      `;
    }

    const moodTrigger = moodContainer.querySelector(".add-mood-btn, .change-mood-btn");
    if (moodTrigger) {
      moodTrigger.addEventListener("click", () => promptMoodCheckin(dateStr, dayData.mood_checkin));
    }
  }

  // Transactions Section
  if (txCountEl) {
    txCountEl.textContent = `${dayData.expenses.length} entr${dayData.expenses.length === 1 ? 'y' : 'ies'}`;
  }

  if (expensesListEl) {
    if (dayData.expenses.length === 0) {
      expensesListEl.innerHTML = `
        <div class="inspector-empty-box">
          <i data-lucide="check-circle-2" style="width: 28px; height: 28px; stroke: var(--brand-forest); margin-bottom: 6px;"></i>
          <div style="font-size: 0.875rem; font-weight: 700; color: var(--ink-primary); margin-bottom: 2px;">Nothing spent on this day.</div>
          <div style="font-size: 0.75rem;">Your wallet enjoyed calm stillness.</div>
        </div>
      `;
    } else {
      expensesListEl.innerHTML = dayData.expenses.map(exp => {
        const iconName = CATEGORY_ICONS[exp.category] || "tag";
        const splitTag = exp.is_split
          ? `<span class="activity-pill pill-split">Split ÷ ${exp.split_count}</span>`
          : "";
        const displayTitle = exp.note ? exp.note : exp.category;

        return `
          <div class="cal-expense-row" data-id="${exp.id}">
            <div class="cal-expense-left">
              <div class="cal-expense-icon">
                <i data-lucide="${iconName}" class="lucide-icon" style="width: 15px; height: 15px;"></i>
              </div>
              <div class="cal-expense-info">
                <div class="cal-expense-title">${displayTitle}</div>
                <div class="cal-expense-meta">
                  <span class="activity-pill">${exp.category}</span>
                  <span class="activity-pill">${exp.mood_tag}</span>
                  ${splitTag}
                </div>
              </div>
            </div>
            <div class="cal-expense-right">
              <span class="cal-expense-amt tnum">₹${parseFloat(exp.amount).toFixed(2)}</span>
              <div class="cal-expense-actions">
                <button type="button" class="btn-cal-action cal-edit-btn" data-id="${exp.id}" title="Edit expense" aria-label="Edit expense">
                  <i data-lucide="edit-3" style="width: 13px; height: 13px; stroke: var(--ink-secondary);"></i>
                </button>
                <button type="button" class="btn-cal-action cal-delete-btn" data-id="${exp.id}" title="Delete expense" aria-label="Delete expense">
                  <i data-lucide="trash-2" style="width: 13px; height: 13px; stroke: #B91C1C;"></i>
                </button>
              </div>
            </div>
          </div>
        `;
      }).join("");

      // Wire up inline Edit handlers
      expensesListEl.querySelectorAll(".cal-edit-btn").forEach(btn => {
        btn.addEventListener("click", () => {
          const id = parseInt(btn.getAttribute("data-id"), 10);
          const item = dayData.expenses.find(x => x.id === id);
          if (item && window.openSharedEditModal) {
            window.openSharedEditModal(item, () => {
              loadCalendarMonth(calYear, calMonth);
            });
          }
        });
      });

      // Wire up inline Delete handlers with 5-second undo toast
      expensesListEl.querySelectorAll(".cal-delete-btn").forEach(btn => {
        btn.addEventListener("click", () => {
          const id = parseInt(btn.getAttribute("data-id"), 10);
          handleDeleteCalendarExpense(id);
        });
      });
    }
  }

  // Bottom Action Button
  if (logBtnText) {
    logBtnText.textContent = `+ Log Expense for ${shortDateStr}`;
  }
  if (logBtn) {
    logBtn.href = `/log-expense?date=${dateStr}`;
  }

  if (window.lucide) {
    window.lucide.createIcons();
  }
}

async function handleDeleteCalendarExpense(expenseId) {
  try {
    const res = await fetch(`/api/expenses/${expenseId}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Could not delete expense");

    if (typeof showToast === "function") {
      showToast("Expense removed.", "info", {
        label: "Undo",
        callback: async () => {
          try {
            const restoreRes = await fetch("/api/expenses/restore", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ expense_id: expenseId })
            });
            if (restoreRes.ok) {
              showToast("Expense restored.", "success");
              loadCalendarMonth(calYear, calMonth);
            }
          } catch (err) {
            showToast("Failed to restore expense.", "error");
          }
        }
      });
    }

    loadCalendarMonth(calYear, calMonth);
  } catch (err) {
    if (typeof showToast === "function") {
      showToast(err.message, "error");
    }
  }
}

async function promptMoodCheckin(dateStr, currentMood) {
  const moods = ["Calm", "Confident", "Neutral", "Anxious", "Stressed"];
  const choice = prompt(
    `Check-in Wallet Mood for ${dateStr}:\nEnter one of: ${moods.join(", ")}`,
    currentMood || "Calm"
  );
  if (!choice) return;

  const normalized = choice.trim();
  if (!normalized) return;

  try {
    const res = await fetch("/api/mood-checkin", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ date: dateStr, mood: normalized })
    });
    if (!res.ok) throw new Error("Failed to record mood check-in.");
    if (typeof showToast === "function") {
      showToast(`Mood check-in recorded: ${normalized}`, "success");
    }
    loadCalendarMonth(calYear, calMonth);
  } catch (err) {
    if (typeof showToast === "function") {
      showToast(err.message, "error");
    }
  }
}

function setupCalendarControls() {
  const prevBtn = document.getElementById("calPrevMonthBtn");
  const nextBtn = document.getElementById("calNextMonthBtn");
  const todayBtn = document.getElementById("calTodayBtn");

  if (prevBtn) {
    prevBtn.addEventListener("click", () => {
      if (calMonth === 1) {
        calMonth = 12;
        calYear -= 1;
      } else {
        calMonth -= 1;
      }
      loadCalendarMonth(calYear, calMonth);
    });
  }

  if (nextBtn) {
    nextBtn.addEventListener("click", () => {
      if (calMonth === 12) {
        calMonth = 1;
        calYear += 1;
      } else {
        calMonth += 1;
      }
      loadCalendarMonth(calYear, calMonth);
    });
  }

  if (todayBtn) {
    todayBtn.addEventListener("click", () => {
      const now = new Date();
      calYear = now.getFullYear();
      calMonth = now.getMonth() + 1;
      calSelectedDate = now.toISOString().slice(0, 10);
      loadCalendarMonth(calYear, calMonth);
    });
  }
}

document.addEventListener("DOMContentLoaded", () => {
  if (document.getElementById("calendarGridDays")) {
    setupCalendarControls();
    loadCalendarMonth(calYear, calMonth);
  }
});
