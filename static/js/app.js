/**
 * app.js - Client-Side Interactive Engine for SpendCalm Fintech Web App.
 * Coordinates:
 * - Real-time Safe-to-Spend & 3-column KPI updates (Overview)
 * - Insights analytics directly on Overview (Doughnut breakdown, 7-Day Trend, Habit Stories)
 * - Dedicated rapid expense logger (/log-expense) with live today feedback panel & preset manager
 * - Full ledger view with live multi-filter search, edit modal, and 5-sec undo (/transactions)
 * - Hostel roommate splits with 1-click settlement and recurring monthly bills (/splits-bills)
 * - 48-Hour Impulse Cooldown wishlist (/cooldown)
 * - SpendCalm Buddy slide-over AI assistant
 * - Anonymized participant switcher modal
 */

// Global State
let insightsDoughnutChart = null;
let insightsTrendChart = null;
let logInteractionStartTime = null;

// Editorial Color Palettes
const CATEGORY_COLORS = {
  "Food": "#1B4332",
  "Travel": "#4A6FA5",
  "Hostel/PG": "#C9A66B",
  "Fun": "#C06C52",
  "Misc": "#6B7280"
};

const MOOD_COLORS = {
  "Essential": "#1B4332",
  "Craving": "#D97706",
  "Friends": "#4A6FA5",
  "Impulse": "#C06C52"
};

// =========================================================================
// Toast Notification Engine (Monochrome Fintech Style + Undo Support)
// =========================================================================

function showToast(message, type = "info", action = null) {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = "fintech-toast";

  let iconName = "info";
  if (type === "success") iconName = "check-circle";
  if (type === "warning") iconName = "alert-circle";
  if (type === "error") iconName = "alert-triangle";

  let actionHtml = "";
  if (action && action.label) {
    actionHtml = `<button type="button" class="toast-undo-btn">${action.label}</button>`;
  }

  toast.innerHTML = `
    <i data-lucide="${iconName}" class="lucide-icon" style="stroke: #FFFFFF; width: 16px; height: 16px;"></i>
    <span style="flex: 1;">${message}</span>
    ${actionHtml}
  `;
  container.appendChild(toast);

  if (window.lucide) {
    window.lucide.createIcons();
  }

  if (action && action.callback) {
    const btn = toast.querySelector(".toast-undo-btn");
    if (btn) {
      btn.addEventListener("click", () => {
        action.callback();
        toast.remove();
      });
    }
  }

  const duration = action ? 6000 : 3200;
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(-6px)";
    toast.style.transition = "all 0.25s ease";
    setTimeout(() => toast.remove(), 250);
  }, duration);
}

// =========================================================================
// Overview Dashboard & Safe-to-Spend Sync
// =========================================================================

async function fetchDashboardData() {
  try {
    const res = await fetch("/api/dashboard");
    if (!res.ok) throw new Error("Could not load dashboard data");
    const data = await res.json();
    updateDashboardUI(data);
  } catch (err) {
    console.error("Dashboard sync error:", err);
  }
}

function updateDashboardUI(data) {
  const metrics = data.metrics;
  if (!metrics) return;

  // Header Date & Cycle
  const dateEl = document.getElementById("header-date");
  if (dateEl) {
    const now = new Date();
    const options = { weekday: "long", month: "short", day: "numeric" };
    const dateFormatted = now.toLocaleDateString("en-US", options);
    dateEl.textContent = `${dateFormatted} • ${metrics.days_remaining} day${metrics.days_remaining !== 1 ? 's' : ''} left in month`;
  }

  // Safe-to-Spend Figure
  const safeTodayEl = document.getElementById("safe-today-val");
  const coachBoxEl = document.getElementById("coach-box");
  const coachMsgEl = document.getElementById("coach-message");
  const streakValEl = document.getElementById("streak-val");
  const progressFillEl = document.getElementById("budget-progress-fill");

  // Mini KPI row
  const kpiBudgetEl = document.getElementById("kpi-budget");
  const kpiSpentEl = document.getElementById("kpi-spent");
  const kpiRemainingEl = document.getElementById("kpi-remaining");

  if (safeTodayEl) {
    safeTodayEl.textContent = metrics.safe_to_spend_today.toFixed(2);
  }

  if (kpiBudgetEl) {
    kpiBudgetEl.textContent = `₹${metrics.monthly_budget.toLocaleString()}`;
  }
  if (kpiSpentEl) {
    kpiSpentEl.textContent = `₹${metrics.total_spent_month.toFixed(2)}`;
  }
  if (kpiRemainingEl) {
    const remMonth = Math.max(0, metrics.monthly_budget - metrics.total_spent_month);
    kpiRemainingEl.textContent = `₹${remMonth.toFixed(2)}`;
  }

  if (coachBoxEl && coachMsgEl) {
    coachMsgEl.textContent = metrics.coach_message;
    if (metrics.status_tone === "caution") {
      coachBoxEl.classList.add("caution-tone");
    } else {
      coachBoxEl.classList.remove("caution-tone");
    }
  }

  if (streakValEl) {
    streakValEl.textContent = `${metrics.streak} day streak`;
  }

  if (progressFillEl) {
    progressFillEl.style.width = `${Math.min(100, metrics.percent_used)}%`;
    if (metrics.status_tone === "caution") {
      progressFillEl.classList.add("caution-tone");
    } else {
      progressFillEl.classList.remove("caution-tone");
    }
  }

  const usedPctEl = document.getElementById("used-pct-label");
  if (usedPctEl) {
    usedPctEl.textContent = `${metrics.percent_used.toFixed(1)}% used`;
  }

  const statusPill = document.getElementById("hero-status-pill");
  const statusText = document.getElementById("hero-status-text");
  if (statusPill && statusText) {
    if (metrics.status_tone === "caution") {
      statusPill.className = "hero-status-pill status-gentle-pace";
      statusText.textContent = "Gentle Pace";
      const iconEl = statusPill.querySelector("i");
      if (iconEl) iconEl.setAttribute("data-lucide", "alert-triangle");
    } else {
      statusPill.className = "hero-status-pill status-on-track";
      statusText.textContent = "On Track";
      const iconEl = statusPill.querySelector("i");
      if (iconEl) iconEl.setAttribute("data-lucide", "shield-check");
    }
    if (window.lucide) window.lucide.createIcons();
  }

  // Quick Snapshot Card
  const snapTopCat = document.getElementById("snapshot-top-cat");
  const snapPendingSplits = document.getElementById("snapshot-pending-splits");
  const snapCooldownSaved = document.getElementById("snapshot-cooldown-saved");

  if (snapTopCat) {
    snapTopCat.textContent = metrics.top_category || "None";
  }
  if (snapPendingSplits && typeof data.pending_splits_total !== "undefined") {
    snapPendingSplits.textContent = `₹${data.pending_splits_total.toFixed(2)}`;
  }
  if (snapCooldownSaved && typeof data.cooldown_saved_total !== "undefined") {
    snapCooldownSaved.textContent = `₹${data.cooldown_saved_total.toFixed(2)}`;
  }

  // Recent Activity (strictly 5 items on Overview)
  if (data.recent_expenses) {
    renderRecent5List(data.recent_expenses);
  }
}

let recent5ExpensesCache = [];

function renderRecent5List(expenses) {
  const container = document.getElementById("recent-5-list-container");
  if (!container) return;

  recent5ExpensesCache = expenses || [];

  if (!expenses || expenses.length === 0) {
    container.innerHTML = `
      <div style="text-align: center; padding: 28px 16px; color: var(--ink-muted);">
        <i data-lucide="inbox" style="width: 28px; height: 28px; stroke: var(--border-strong); margin-bottom: 6px;"></i>
        <div style="font-size: 0.875rem; font-weight: 700; color: var(--ink-primary); margin-bottom: 2px;">No Activity Yet</div>
        <div style="font-size: 0.75rem;">Log your first expense or tap a preset to begin.</div>
      </div>
    `;
    if (window.lucide) window.lucide.createIcons();
    return;
  }

  const categoryIcons = {
    "Food": "utensils",
    "Travel": "car",
    "Hostel/PG": "home",
    "Fun": "gamepad-2",
    "Misc": "more-horizontal"
  };

  container.innerHTML = expenses.map(exp => {
    const iconName = categoryIcons[exp.category] || "tag";
    const splitPill = exp.is_split
      ? `<span class="activity-pill pill-split">Split ÷ ${exp.split_count}</span>`
      : "";
    const displayNote = exp.note ? exp.note : exp.category;
    const dateStr = exp.expense_date || (exp.created_at ? exp.created_at.slice(5, 10) : "");

    return `
      <div class="activity-row" data-id="${exp.id}">
        <div class="activity-left">
          <div class="activity-icon-box">
            <i data-lucide="${iconName}" class="lucide-icon" style="width: 15px; height: 15px;"></i>
          </div>
          <div class="activity-info">
            <div class="activity-title">${displayNote}</div>
            <div class="activity-meta">
              <span class="activity-pill">${exp.category}</span>
              <span class="activity-pill">${exp.mood_tag}</span>
              ${splitPill}
              ${dateStr ? `<span class="activity-date tnum">${dateStr}</span>` : ""}
            </div>
          </div>
        </div>
        <div class="activity-right">
          <span class="activity-amount tnum">₹${parseFloat(exp.amount).toFixed(2)}</span>
          <div class="activity-hover-actions">
            <button type="button" class="btn-activity-action edit-recent-btn" data-id="${exp.id}" title="Edit transaction" aria-label="Edit transaction">
              <i data-lucide="edit-3" style="width: 13px; height: 13px; stroke: var(--ink-secondary);"></i>
            </button>
            <button type="button" class="btn-activity-action delete-recent-btn" data-id="${exp.id}" title="Delete transaction" aria-label="Delete transaction">
              <i data-lucide="trash-2" style="width: 13px; height: 13px; stroke: #B91C1C;"></i>
            </button>
          </div>
        </div>
      </div>
    `;
  }).join("");

  if (window.lucide) {
    window.lucide.createIcons();
  }

  // Wire up Edit and Delete action buttons
  container.querySelectorAll(".edit-recent-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const id = parseInt(btn.getAttribute("data-id"), 10);
      const item = recent5ExpensesCache.find(x => x.id === id);
      if (item && window.openSharedEditModal) {
        window.openSharedEditModal(item, () => {
          fetchDashboardData();
          loadInsightsData();
        });
      }
    });
  });

  container.querySelectorAll(".delete-recent-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const id = parseInt(btn.getAttribute("data-id"), 10);
      window.handleDeleteRecentExpense(id);
    });
  });
}

window.handleDeleteRecentExpense = async function(id) {
  try {
    const res = await fetch(`/api/expenses/${id}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Could not delete expense");

    showToast("Expense removed.", "info", {
      label: "Undo",
      callback: async () => {
        try {
          const restoreRes = await fetch("/api/expenses/restore", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ expense_id: id })
          });
          if (restoreRes.ok) {
            showToast("Expense restored.", "success");
            fetchDashboardData();
            loadInsightsData();
          }
        } catch (err) {
          showToast("Failed to restore expense.", "error");
        }
      }
    });

    fetchDashboardData();
    loadInsightsData();
  } catch (err) {
    showToast(err.message, "error");
  }
};

// =========================================================================
// Visual Insights & Analytics Engine (Overview Row 2 & Row 3)
// =========================================================================

let insightsDataCache = null;
let activeInsightsTab = "category"; // category | mood

async function loadInsightsData() {
  const doughnutCanvas = document.getElementById("insightsDoughnutChart");
  const trendCanvas = document.getElementById("insightsTrendChart");
  if (!doughnutCanvas || !trendCanvas) return; // Not on page with insights

  try {
    const res = await fetch("/api/insights");
    if (!res.ok) throw new Error("Could not load insights data");
    insightsDataCache = await res.json();
    renderInsightsUI();
  } catch (err) {
    console.error("Insights load error:", err);
  }
}

function renderInsightsUI() {
  if (!insightsDataCache) return;

  // Compact 3-Stat Strip on Trend Card
  const kpiAvg = document.getElementById("kpiDailyAvg");
  const kpiRatio = document.getElementById("kpiRatio");
  const kpiDayAmt = document.getElementById("kpiHighestDayAmt");
  const baselineEl = document.getElementById("trendSafeBaseline");

  if (kpiAvg) kpiAvg.textContent = `₹${insightsDataCache.daily_average_spend.toFixed(2)}`;
  if (kpiRatio) {
    const evn = insightsDataCache.essential_vs_non_essential || {};
    const ePct = evn.essential_pct ?? insightsDataCache.essential_ratio ?? 0;
    const nePct = evn.non_essential_pct ?? insightsDataCache.non_essential_ratio ?? 0;
    kpiRatio.textContent = `${ePct}% / ${nePct}%`;
  }
  if (kpiDayAmt && insightsDataCache.highest_spend_day) {
    kpiDayAmt.textContent = `₹${insightsDataCache.highest_spend_day.amount.toFixed(2)}`;
  }
  if (baselineEl) {
    baselineEl.textContent = `₹${insightsDataCache.safe_daily_reference.toFixed(2)}`;
  }

  renderDoughnutBreakdown();
  renderTrendChart();
  renderHabitStories();
}

function renderDoughnutBreakdown() {
  const doughnutCanvas = document.getElementById("insightsDoughnutChart");
  if (!doughnutCanvas || !insightsDataCache || !window.Chart) return;

  const isCategory = activeInsightsTab === "category";
  const breakdownList = isCategory ? insightsDataCache.category_breakdown : insightsDataCache.intent_breakdown;
  const labels = breakdownList.map(x => isCategory ? x.category : x.intent);
  const dataVals = breakdownList.map(x => x.amount);
  const colors = breakdownList.map(x => x.color);
  const hasData = dataVals.some(v => v > 0);

  // Update center total spend callout
  const totalAmt = hasData ? dataVals.reduce((a, b) => a + b, 0) : 0;
  const centerAmtEl = document.getElementById("doughnut-center-amt");
  if (centerAmtEl) {
    centerAmtEl.textContent = `₹${Math.round(totalAmt)}`;
  }

  if (insightsDoughnutChart) insightsDoughnutChart.destroy();

  insightsDoughnutChart = new Chart(doughnutCanvas, {
    type: "doughnut",
    data: {
      labels: hasData ? labels : ["No data"],
      datasets: [{
        data: hasData ? dataVals : [1],
        backgroundColor: hasData ? colors : ["#E4E4DC"],
        borderWidth: 2,
        borderColor: "#FFFFFF"
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false }
      },
      cutout: "70%"
    }
  });

  // Render Clean Itemized Breakdown List with Dot, Label, Amount, and Pct
  const listContainer = document.getElementById("insightsItemList");
  if (listContainer) {
    listContainer.innerHTML = breakdownList.map(item => {
      const title = isCategory ? item.category : item.intent;
      const pctDisplay = Math.round(item.percentage);
      return `
        <div class="breakdown-item-row">
          <div class="breakdown-left">
            <span class="breakdown-dot" style="background-color: ${item.color};"></span>
            <span style="font-weight: 700; color: var(--ink-primary);">${title}</span>
          </div>
          <div class="breakdown-right">
            <span class="tnum" style="font-weight: 800; color: var(--ink-primary);">₹${item.amount.toFixed(2)}</span>
            <span class="breakdown-pct-badge tnum">${pctDisplay}%</span>
          </div>
        </div>
      `;
    }).join("");
  }
}

function renderTrendChart() {
  const trendCanvas = document.getElementById("insightsTrendChart");
  if (!trendCanvas || !insightsDataCache || !window.Chart) return;

  const trend = insightsDataCache.seven_day_trend;
  const safeBaseline = insightsDataCache.safe_daily_reference;

  if (insightsTrendChart) insightsTrendChart.destroy();

  // Baseline dataset (horizontal line)
  const baselineData = trend.labels.map(() => safeBaseline);

  insightsTrendChart = new Chart(trendCanvas, {
    type: "bar",
    data: {
      labels: trend.labels,
      datasets: [
        {
          type: "line",
          label: "Daily Target",
          data: baselineData,
          borderColor: "#C06C52",
          borderWidth: 2,
          borderDash: [5, 4],
          pointRadius: 0,
          fill: false
        },
        {
          type: "bar",
          label: "Daily Spend",
          data: trend.values,
          backgroundColor: "#1B4332",
          borderRadius: 6
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "bottom",
          labels: {
            boxWidth: 10,
            padding: 8,
            font: { family: "Plus Jakarta Sans", size: 10, weight: 600 },
            color: "#52525B"
          }
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { font: { family: "Plus Jakarta Sans", size: 10 }, color: "#71717A" }
        },
        y: {
          beginAtZero: true,
          grid: { color: "#F0F0EB" },
          ticks: {
            font: { family: "Plus Jakarta Sans", size: 10 },
            color: "#71717A",
            callback: val => `₹${val}`
          }
        }
      }
    }
  });
}

function renderHabitStories() {
  const container = document.getElementById("insightsStoriesList");
  if (!container || !insightsDataCache || !insightsDataCache.stories) return;

  container.innerHTML = insightsDataCache.stories.map(story => `
    <div class="story-bubble">
      <i data-lucide="info" class="lucide-icon" style="stroke: var(--brand-forest); width: 16px; height: 16px; margin-top: 2px;"></i>
      <div>${story}</div>
    </div>
  `).join("");

  // Month-end pace projection calculation
  const projEl = document.getElementById("habitProjectionText");
  if (projEl && insightsDataCache) {
    const dailyAvg = insightsDataCache.daily_average_spend || 0;
    const now = new Date();
    const daysInMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
    const todayDate = now.getDate();
    const daysRemaining = Math.max(1, (daysInMonth - todayDate) + 1);
    const projectedRemaining = dailyAvg * daysRemaining;
    const monthlyBudget = insightsDataCache.monthly_budget || 3000;
    const spentSoFar = insightsDataCache.total_spent_month || 0;
    const projectedTotal = spentSoFar + projectedRemaining;
    const delta = monthlyBudget - projectedTotal;

    if (delta >= 0) {
      projEl.innerHTML = `At your current pace of <strong class="tnum">₹${dailyAvg.toFixed(2)}/day</strong>, you're projected to finish the month with a calm surplus of <strong class="tnum" style="color: var(--brand-forest);">₹${delta.toFixed(2)}</strong>.`;
    } else {
      projEl.innerHTML = `At your current pace of <strong class="tnum">₹${dailyAvg.toFixed(2)}/day</strong>, you're pacing <strong class="tnum" style="color: #B45309;">₹${Math.abs(delta).toFixed(2)}</strong> over budget by month end. A slight adjustment will restore calm.`;
    }
  }

  if (window.lucide) window.lucide.createIcons();
}

function setupInsightsTabs() {
  const tabCatBtn = document.getElementById("insightsTabCatBtn");
  const tabMoodBtn = document.getElementById("insightsTabMoodBtn");

  if (!tabCatBtn || !tabMoodBtn) return;

  tabCatBtn.addEventListener("click", () => {
    tabCatBtn.classList.add("active");
    tabMoodBtn.classList.remove("active");
    tabCatBtn.setAttribute("aria-selected", "true");
    tabMoodBtn.setAttribute("aria-selected", "false");
    activeInsightsTab = "category";
    renderDoughnutBreakdown();
  });

  tabMoodBtn.addEventListener("click", () => {
    tabMoodBtn.classList.add("active");
    tabCatBtn.classList.remove("active");
    tabMoodBtn.setAttribute("aria-selected", "true");
    tabCatBtn.setAttribute("aria-selected", "false");
    activeInsightsTab = "mood";
    renderDoughnutBreakdown();
  });
}

// =========================================================================
// =========================================================================
// Category Management & Dynamic Synchronization Engine
// =========================================================================

let userCategoriesCache = [];
let currentSafeToSpendToday = 0;
let todayExpensesCache = [];

async function loadUserCategories() {
  try {
    const res = await fetch("/api/categories");
    if (!res.ok) return;
    const data = await res.json();
    userCategoriesCache = data.categories || [];

    renderCategoryPills();
    renderCategoriesManagerList();
    populateCategoryDropdowns();
    renderPresetsStrip();
  } catch (err) {
    console.error("Error loading categories:", err);
  }
}

function populateCategoryDropdowns() {
  const selects = document.querySelectorAll("#editCategory, .preset-field-category");
  selects.forEach(sel => {
    const currVal = sel.value;
    sel.innerHTML = userCategoriesCache.map(cat => `
      <option value="${cat.name}" ${cat.name.toLowerCase() === currVal.toLowerCase() ? 'selected' : ''}>${cat.name}</option>
    `).join("");
  });
}

function renderCategoryPills() {
  const container = document.getElementById("category-pills-container");
  if (!container || userCategoriesCache.length === 0) return;

  const currentChecked = container.querySelector('input[name="category"]:checked')?.value || "Food";

  container.innerHTML = userCategoriesCache.map((cat, idx) => {
    const isChecked = cat.name.toLowerCase() === currentChecked.toLowerCase() || (!currentChecked && idx === 0);
    const iconName = cat.icon || "tag";
    return `
      <div class="pill-check-option">
        <input type="radio" id="cat-opt-${cat.id}" name="category" value="${cat.name}" ${isChecked ? 'checked' : ''}>
        <label for="cat-opt-${cat.id}" class="pill-check-label">
          <i data-lucide="${iconName}" class="lucide-icon" style="width: 14px; height: 14px;"></i>
          <span>${cat.name}</span>
        </label>
      </div>
    `;
  }).join("");

  if (window.lucide) window.lucide.createIcons();
}

function setupCategoryManager() {
  const modal = document.getElementById("manage-categories-modal");
  const openBtn = document.getElementById("open-manage-categories-btn");
  const closeBtn = document.getElementById("close-manage-categories-btn");
  const doneBtn = document.getElementById("done-categories-btn");
  const addBtn = document.getElementById("add-category-btn");
  const nameInput = document.getElementById("new-cat-name");

  if (!modal) return;

  let selectedIcon = "shirt";
  let selectedColor = "#1B4332";

  function openModal() {
    renderCategoriesManagerList();
    modal.classList.add("open");
  }

  function closeModal() {
    modal.classList.remove("open");
  }

  if (openBtn) openBtn.addEventListener("click", openModal);
  if (closeBtn) closeBtn.addEventListener("click", closeModal);
  if (doneBtn) doneBtn.addEventListener("click", closeModal);

  // Icon picker
  const iconBtns = modal.querySelectorAll("#new-cat-icon-picker .icon-picker-btn");
  iconBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      iconBtns.forEach(b => b.classList.remove("selected"));
      btn.classList.add("selected");
      selectedIcon = btn.getAttribute("data-icon") || "tag";
    });
  });

  // Color picker
  const colorSwatches = modal.querySelectorAll("#new-cat-color-picker .color-picker-swatch");
  colorSwatches.forEach(swatch => {
    swatch.addEventListener("click", () => {
      colorSwatches.forEach(s => s.classList.remove("selected"));
      swatch.classList.add("selected");
      selectedColor = swatch.getAttribute("data-color") || "#6B7280";
    });
  });

  // Add Category button
  if (addBtn) {
    addBtn.addEventListener("click", async () => {
      const name = (nameInput?.value || "").trim();
      if (name.length < 2 || name.length > 20) {
        showToast("Category name must be between 2 and 20 characters.", "error");
        if (nameInput) nameInput.focus();
        return;
      }

      try {
        const res = await fetch("/api/categories", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name, icon: selectedIcon, color: selectedColor })
        });

        if (!res.ok) {
          const errData = await res.json();
          throw new Error(errData.error || "Could not add category");
        }

        if (nameInput) nameInput.value = "";
        showToast(`Category "${name}" created.`, "success");
        await loadUserCategories();
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  }
}

function renderCategoriesManagerList() {
  const container = document.getElementById("categories-manager-list");
  if (!container) return;

  container.innerHTML = userCategoriesCache.map(cat => {
    const isMisc = cat.name.toLowerCase() === "misc";
    const deleteBtn = isMisc
      ? `<span class="category-badge-default">Default Fallback</span>`
      : `<button type="button" class="btn-table-action delete delete-cat-btn" data-id="${cat.id}" data-name="${cat.name}" title="Delete category" aria-label="Delete category"><i data-lucide="trash-2" style="width: 13px; height: 13px;"></i></button>`;

    const editBtn = `
      <button type="button" class="btn-table-action edit-cat-btn" data-id="${cat.id}" data-name="${cat.name}" data-icon="${cat.icon || 'tag'}" data-color="${cat.color || '#6B7280'}" title="Rename category" aria-label="Rename category">
        <i data-lucide="pencil" style="width: 13px; height: 13px;"></i>
      </button>
    `;

    return `
      <div class="category-manage-item">
        <div class="category-meta-left">
          <span class="category-color-dot" style="background-color: ${cat.color};"></span>
          <i data-lucide="${cat.icon || 'tag'}" class="lucide-icon" style="width: 14px; height: 14px; stroke: var(--ink-secondary);"></i>
          <span class="category-name-text">${cat.name}</span>
        </div>
        <div style="display: flex; align-items: center; gap: 4px;">
          ${editBtn}
          ${deleteBtn}
        </div>
      </div>
    `;
  }).join("");

  if (window.lucide) window.lucide.createIcons();

  // Attach delete handlers
  container.querySelectorAll(".delete-cat-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      const catId = btn.getAttribute("data-id");
      const catName = btn.getAttribute("data-name");
      if (!confirm(`Delete category "${catName}"? Existing expenses and bills will be safely reassigned to "Misc".`)) {
        return;
      }
      try {
        const res = await fetch(`/api/categories/${catId}`, { method: "DELETE" });
        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.error || "Failed to delete category");
        }
        showToast(`Category "${catName}" deleted. Expenses moved to Misc.`, "info");
        await loadUserCategories();
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  });

  // Attach edit/rename handlers
  container.querySelectorAll(".edit-cat-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      const catId = btn.getAttribute("data-id");
      const currentName = btn.getAttribute("data-name");
      const currentIcon = btn.getAttribute("data-icon");
      const currentColor = btn.getAttribute("data-color");
      const newName = prompt(`Rename category "${currentName}" (2-20 characters):`, currentName);
      if (!newName || newName.trim() === currentName) return;
      const cleanName = newName.trim();
      if (cleanName.length < 2 || cleanName.length > 20) {
        showToast("Category name must be between 2 and 20 characters.", "error");
        return;
      }
      try {
        const res = await fetch(`/api/categories/${catId}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: cleanName, icon: currentIcon, color: currentColor })
        });
        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.error || "Failed to update category");
        }
        showToast(`Category renamed to "${cleanName}".`, "success");
        await loadUserCategories();
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  });
}

// =========================================================================
// Customizable Presets Engine with 1-Tap Instant Save (2 to 6 Presets)
// =========================================================================

const DEFAULT_PRESETS = [
  { name: "Chai", amount: 20, category: "Food", mood: "Essential", note: "Chai at gate" },
  { name: "Auto", amount: 50, category: "Travel", mood: "Essential", note: "Campus auto" },
  { name: "Tiffin", amount: 80, category: "Food", mood: "Essential", note: "Mess lunch" },
  { name: "Snacks", amount: 100, category: "Food", mood: "Craving", note: "Evening snacks" }
];

function isInstantSaveEnabled() {
  return localStorage.getItem("spendcalm_instant_save") === "true";
}

function setupInstantSaveToggle() {
  const toggle = document.getElementById("instant-save-toggle");
  if (!toggle) return;
  toggle.checked = isInstantSaveEnabled();

  toggle.addEventListener("change", () => {
    localStorage.setItem("spendcalm_instant_save", toggle.checked ? "true" : "false");
    showToast(
      toggle.checked
        ? "1-Tap Instant Save ON: presets log immediately with 5s undo."
        : "1-Tap Instant Save OFF: presets fill form for manual review.",
      "info"
    );
  });
}

function getSavedPresets() {
  try {
    const saved = localStorage.getItem("spendcalm_custom_presets");
    if (saved) {
      const parsed = JSON.parse(saved);
      if (Array.isArray(parsed) && parsed.length >= 2 && parsed.length <= 6) {
        return parsed;
      }
    }
  } catch (e) {
    console.warn("Could not load presets from localStorage", e);
  }
  return DEFAULT_PRESETS;
}

function savePresets(presets) {
  try {
    localStorage.setItem("spendcalm_custom_presets", JSON.stringify(presets));
  } catch (e) {
    console.warn("Could not save presets to localStorage", e);
  }
}

function renderPresetsStrip() {
  const container = document.getElementById("presets-strip-container");
  if (!container) return;

  const presets = getSavedPresets();

  container.innerHTML = presets.map((p, idx) => {
    const catObj = userCategoriesCache.find(c => c.name.toLowerCase() === p.category.toLowerCase());
    const iconName = catObj?.icon || "coffee";
    return `
      <button type="button" class="preset-chip-btn dynamic-preset-btn" data-preset-idx="${idx}" aria-label="Quick preset ${p.name}">
        <i data-lucide="${iconName}" class="lucide-icon" style="width: 14px; height: 14px;"></i>
        <span>${p.name} <strong>₹${p.amount}</strong></span>
      </button>
    `;
  }).join("");

  if (window.lucide) window.lucide.createIcons();

  // Attach click handlers to dynamic preset chips
  const dynamicBtns = container.querySelectorAll(".dynamic-preset-btn");
  const amountInput = document.getElementById("log-amount");
  const noteInput = document.getElementById("log-note");
  const form = document.getElementById("rapid-logger-form");
  const submitBtn = document.getElementById("logger-submit-btn");

  dynamicBtns.forEach(btn => {
    btn.addEventListener("click", async () => {
      const idx = parseInt(btn.getAttribute("data-preset-idx"), 10);
      const config = presets[idx];
      if (!config) return;

      if (isInstantSaveEnabled()) {
        // 1-Tap Instant Save: Call POST /api/expenses directly
        const dateInputEl = document.getElementById("log-date");
        const targetDateStr = (dateInputEl && dateInputEl.value) ? dateInputEl.value : new Date().toISOString().slice(0, 10);
        const payload = {
          amount: config.amount,
          category: config.category,
          mood_tag: config.mood || "Essential",
          is_split: false,
          split_count: 1,
          note: config.note || config.name,
          expense_date: targetDateStr
        };

        try {
          const res = await fetch("/api/expenses", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
          });
          if (!res.ok) {
            const errData = await res.json();
            throw new Error(errData.error || "Failed to log preset spend");
          }
          const data = await res.json();
          const expId = data.expense_id;

          showToast(`Saved ₹${config.amount} for ${config.name} • 5s Undo`, "success", {
            label: "Undo",
            callback: async () => {
              await fetch("/api/expenses/restore", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ expense_id: expId })
              });
              showToast("Preset spend undone.", "info");
              fetchLiveTodayData();
            }
          });

          fetchLiveTodayData();
          if (document.getElementById("safe-today-val")) {
            fetchDashboardData();
            loadInsightsData();
          }
        } catch (err) {
          showToast(err.message, "error");
        }
      } else {
        // Fill form fields for rapid review
        if (amountInput) amountInput.value = config.amount;
        if (noteInput) noteInput.value = config.note;

        const catRadio = form?.querySelector(`input[name="category"][value="${config.category}"]`);
        if (catRadio) catRadio.checked = true;

        const moodRadio = form?.querySelector(`input[name="mood_tag"][value="${config.mood}"]`);
        if (moodRadio) moodRadio.checked = true;

        updateSplitPreview();
        updateSubmitButtonImpact();
        if (amountInput) amountInput.focus();
      }
    });
  });
}

function getPresetsFromModal() {
  const container = document.getElementById("preset-inputs-container");
  if (!container) return [];
  const cards = container.querySelectorAll(".preset-edit-card");
  const result = [];
  cards.forEach((card, i) => {
    const name = card.querySelector(".preset-field-name")?.value.trim() || `Item ${i + 1}`;
    const amount = parseFloat(card.querySelector(".preset-field-amount")?.value) || 20;
    const category = card.querySelector(".preset-field-category")?.value || "Food";
    const note = card.querySelector(".preset-field-note")?.value.trim() || name;
    result.push({ name, amount, category, mood: "Essential", note });
  });
  return result;
}

function populatePresetModalFields() {
  const container = document.getElementById("preset-inputs-container");
  if (!container) return;

  const presets = getSavedPresets();
  container.innerHTML = presets.map((p, i) => {
    const catOptions = userCategoriesCache.length > 0
      ? userCategoriesCache.map(cat => `
          <option value="${cat.name}" ${cat.name.toLowerCase() === p.category.toLowerCase() ? 'selected' : ''}>${cat.name}</option>
        `).join("")
      : ['Food', 'Travel', 'Hostel/PG', 'Fun', 'Misc'].map(c => `
          <option value="${c}" ${c.toLowerCase() === p.category.toLowerCase() ? 'selected' : ''}>${c}</option>
        `).join("");

    const removeBtn = presets.length > 2
      ? `<button type="button" class="btn-table-action delete remove-preset-row-btn" data-row-idx="${i}" title="Remove preset" aria-label="Remove preset"><i data-lucide="trash-2" style="width: 13px; height: 13px;"></i></button>`
      : ``;

    return `
      <div class="preset-edit-card" data-row-idx="${i}" style="background-color: var(--bg-subtle); padding: 12px; border-radius: var(--radius-input); border: 1px solid var(--border-hairline);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
          <span style="font-size: 0.75rem; font-weight: 700; color: var(--ink-secondary); text-transform: uppercase;">Preset #${i + 1}</span>
          ${removeBtn}
        </div>
        <div class="form-grid-row" style="grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 8px;">
          <div>
            <label style="font-size: 0.6875rem; font-weight: 600; color: var(--ink-muted); display: block; margin-bottom: 3px;">Name</label>
            <input type="text" class="fintech-input preset-field-name" value="${p.name}" placeholder="e.g. Chai" maxlength="20" style="height: 34px; font-size: 0.8125rem;" required>
          </div>
          <div>
            <label style="font-size: 0.6875rem; font-weight: 600; color: var(--ink-muted); display: block; margin-bottom: 3px;">Amount (₹)</label>
            <input type="number" class="fintech-input tnum preset-field-amount" value="${p.amount}" placeholder="20" min="1" step="any" style="height: 34px; font-size: 0.8125rem;" required>
          </div>
        </div>
        <div class="form-grid-row" style="grid-template-columns: 1fr 1.3fr; gap: 8px;">
          <div>
            <label style="font-size: 0.6875rem; font-weight: 600; color: var(--ink-muted); display: block; margin-bottom: 3px;">Category</label>
            <select class="fintech-input preset-field-category" style="height: 34px; font-size: 0.8125rem; font-weight: 600;">
              ${catOptions}
            </select>
          </div>
          <div>
            <label style="font-size: 0.6875rem; font-weight: 600; color: var(--ink-muted); display: block; margin-bottom: 3px;">Default Note</label>
            <input type="text" class="fintech-input preset-field-note" value="${p.note || ''}" placeholder="Memory note" maxlength="50" style="height: 34px; font-size: 0.75rem;">
          </div>
        </div>
      </div>
    `;
  }).join("");

  if (window.lucide) window.lucide.createIcons();

  container.querySelectorAll(".remove-preset-row-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const idx = parseInt(btn.getAttribute("data-row-idx"), 10);
      const curr = getPresetsFromModal();
      if (curr.length > 2) {
        curr.splice(idx, 1);
        savePresets(curr);
        populatePresetModalFields();
      }
    });
  });
}

function setupPresetCustomizer() {
  const modal = document.getElementById("preset-customizer-modal");
  const openBtn = document.getElementById("open-preset-modal-btn");
  const closeBtn = document.getElementById("close-preset-modal");
  const form = document.getElementById("preset-customizer-form");
  const resetBtn = document.getElementById("reset-default-presets-btn");
  const addRowBtn = document.getElementById("add-preset-row-btn");

  if (!modal) return;

  function openModal() {
    populatePresetModalFields();
    modal.classList.add("open");
  }

  function closeModal() {
    modal.classList.remove("open");
  }

  if (openBtn) openBtn.addEventListener("click", openModal);
  if (closeBtn) closeBtn.addEventListener("click", closeModal);

  if (addRowBtn) {
    addRowBtn.addEventListener("click", () => {
      const curr = getPresetsFromModal();
      if (curr.length >= 6) {
        showToast("Maximum 6 presets allowed.", "info");
        return;
      }
      curr.push({
        name: `Item ${curr.length + 1}`,
        amount: 30,
        category: userCategoriesCache[0]?.name || "Food",
        mood: "Essential",
        note: ""
      });
      savePresets(curr);
      populatePresetModalFields();
    });
  }

  if (resetBtn) {
    resetBtn.addEventListener("click", () => {
      savePresets(DEFAULT_PRESETS);
      populatePresetModalFields();
      renderPresetsStrip();
      closeModal();
      showToast("Presets reset to college defaults.", "info");
    });
  }

  if (form) {
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const newPresets = getPresetsFromModal();
      if (newPresets.length < 2) {
        showToast("Minimum 2 presets required.", "error");
        return;
      }
      savePresets(newPresets);
      renderPresetsStrip();
      closeModal();
      showToast("Custom presets saved to browser.", "success");
    });
  }
}

function updateSplitPreview() {
  const splitPreviewText = document.getElementById("split-preview-text");
  const amountInput = document.getElementById("log-amount");
  const splitToggle = document.getElementById("split-toggle");
  const splitCountVal = document.getElementById("split-count-val");

  if (!splitPreviewText || !amountInput) return;
  const rawAmt = parseFloat(amountInput.value) || 0;
  const splitCount = parseInt(splitCountVal?.textContent || "2", 10);

  if (splitToggle && splitToggle.checked && rawAmt > 0) {
    const share = (rawAmt / splitCount).toFixed(2);
    splitPreviewText.textContent = `Your share: ₹${share} (total ₹${rawAmt} ÷ ${splitCount})`;
  } else {
    splitPreviewText.textContent = "";
  }
}

function updateSubmitButtonImpact() {
  const amountInput = document.getElementById("log-amount");
  const submitText = document.getElementById("logger-submit-text");
  const submitBtn = document.getElementById("logger-submit-btn");
  if (!submitText || !submitBtn) return;

  const rawAmt = parseFloat(amountInput?.value) || 0;
  if (rawAmt <= 0) {
    submitText.textContent = "Save Expense";
    submitBtn.classList.remove("pace-adjust");
    return;
  }

  if (rawAmt <= currentSafeToSpendToday) {
    const leftSafe = (currentSafeToSpendToday - rawAmt).toFixed(2);
    submitText.textContent = `Save ₹${rawAmt} • ₹${leftSafe} left safe today`;
    submitBtn.classList.remove("pace-adjust");
  } else {
    submitText.textContent = `Save ₹${rawAmt} • gently adjusts daily pace`;
    submitBtn.classList.add("pace-adjust");
  }
}

function setupQuickBumps() {
  const amountInput = document.getElementById("log-amount");
  const bumpBtns = document.querySelectorAll(".quick-bump-row .bump-pill");

  bumpBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const bump = btn.getAttribute("data-bump");
      if (bump === "clear") {
        if (amountInput) amountInput.value = "";
      } else {
        const addVal = parseFloat(bump) || 0;
        const currentVal = parseFloat(amountInput?.value) || 0;
        const newVal = currentVal + addVal;
        if (amountInput) amountInput.value = newVal % 1 !== 0 ? newVal.toFixed(2) : newVal;
      }
      updateSplitPreview();
      updateSubmitButtonImpact();
      if (amountInput) amountInput.focus();
    });
  });
}

// =========================================================================
// Shared Edit Transaction Modal (Reused across Ledger & Logged Today)
// =========================================================================

let currentEditSaveCallback = null;

function setupSharedEditModal() {
  const modal = document.getElementById("editExpenseModal");
  const form = document.getElementById("editExpenseForm");
  const closeBtn = document.getElementById("closeEditModalBtn");
  const cancelBtn = document.getElementById("cancelEditModalBtn");
  const editSplitToggle = document.getElementById("editSplitToggle");
  const editSplitControls = document.getElementById("editSplitControls");
  const editSplitCountVal = document.getElementById("editSplitCountVal");
  const editSplitDecBtn = document.getElementById("editSplitDecBtn");
  const editSplitIncBtn = document.getElementById("editSplitIncBtn");

  if (!modal || !form) return;

  let editSplitCount = 2;

  function closeEditModal() {
    modal.classList.remove("open");
  }

  if (closeBtn) closeBtn.addEventListener("click", closeEditModal);
  if (cancelBtn) cancelBtn.addEventListener("click", closeEditModal);

  if (editSplitToggle && editSplitControls) {
    editSplitToggle.addEventListener("change", () => {
      editSplitControls.style.display = editSplitToggle.checked ? "flex" : "none";
    });
  }

  if (editSplitIncBtn && editSplitDecBtn && editSplitCountVal) {
    editSplitIncBtn.addEventListener("click", () => {
      editSplitCount = Math.min(10, editSplitCount + 1);
      editSplitCountVal.textContent = editSplitCount;
    });
    editSplitDecBtn.addEventListener("click", () => {
      editSplitCount = Math.max(2, editSplitCount - 1);
      editSplitCountVal.textContent = editSplitCount;
    });
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = document.getElementById("editExpenseId").value;
    const rawAmt = parseFloat(document.getElementById("editAmount").value);
    const dateVal = document.getElementById("editDate").value;
    const noteVal = document.getElementById("editNote").value.trim();
    const catVal = document.getElementById("editCategory").value;
    const moodVal = document.getElementById("editMood").value;
    const isSplit = editSplitToggle ? editSplitToggle.checked : false;
    const splitWith = document.getElementById("editSplitWith")?.value.trim() || "";

    if (!rawAmt || rawAmt <= 0) {
      showToast("Amount must be greater than zero.", "error");
      return;
    }

    const payload = {
      amount: rawAmt,
      expense_date: dateVal,
      note: noteVal,
      category: catVal,
      mood_tag: moodVal,
      is_split: isSplit,
      split_count: isSplit ? editSplitCount : 1,
      split_with: splitWith
    };

    try {
      const res = await fetch(`/api/expenses/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.error || "Failed to update expense");
      }

      showToast("Transaction updated.", "success");
      closeEditModal();
      if (typeof currentEditSaveCallback === "function") {
        currentEditSaveCallback();
      }
    } catch (err) {
      showToast(err.message, "error");
    }
  });

  window.openSharedEditModal = function(item, onSaveCallback) {
    currentEditSaveCallback = onSaveCallback;
    document.getElementById("editExpenseId").value = item.id;
    document.getElementById("editAmount").value = item.amount;
    document.getElementById("editDate").value = item.expense_date || (item.created_at ? item.created_at.slice(0, 10) : "");
    document.getElementById("editNote").value = item.note || "";

    const catSelect = document.getElementById("editCategory");
    if (catSelect && userCategoriesCache.length > 0) {
      catSelect.innerHTML = userCategoriesCache.map(cat => `
        <option value="${cat.name}" ${cat.name.toLowerCase() === (item.category || '').toLowerCase() ? 'selected' : ''}>${cat.name}</option>
      `).join("");
    }
    if (catSelect) catSelect.value = item.category;

    const moodSelect = document.getElementById("editMood");
    if (moodSelect) moodSelect.value = item.mood_tag;

    if (editSplitToggle && editSplitControls) {
      editSplitToggle.checked = !!item.is_split;
      editSplitControls.style.display = item.is_split ? "flex" : "none";
      editSplitCount = item.split_count || 2;
      if (editSplitCountVal) editSplitCountVal.textContent = editSplitCount;
      const splitWithEl = document.getElementById("editSplitWith");
      if (splitWithEl) splitWithEl.value = item.split_with || "";
    }

    modal.classList.add("open");
  };
}

// =========================================================================
// Keyboard Shortcuts Engine
// =========================================================================

function setupKeyboardShortcuts() {
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      document.querySelectorAll(".modal-layer.open").forEach(modal => {
        modal.classList.remove("open");
      });
    }

    if (e.key === "Enter" && !e.shiftKey) {
      const activeEl = document.activeElement;
      const isLoggingInput = activeEl && (activeEl.id === "log-amount" || activeEl.id === "log-note");
      const hasOpenModal = !!document.querySelector(".modal-layer.open");

      if (isLoggingInput && !hasOpenModal) {
        const form = document.getElementById("rapid-logger-form");
        const amtInput = document.getElementById("log-amount");
        const amt = parseFloat(amtInput?.value) || 0;
        if (amt > 0 && form) {
          e.preventDefault();
          form.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
        }
      }
    }
  });
}

// =========================================================================
// Dedicated Log Expense Page Engine (/log-expense)
// =========================================================================

function setupRapidLogger() {
  const form = document.getElementById("rapid-logger-form");
  if (!form) return;

  const amountInput = document.getElementById("log-amount");
  const dateInput = document.getElementById("log-date");
  const noteInput = document.getElementById("log-note");
  const splitToggle = document.getElementById("split-toggle");
  const splitControls = document.getElementById("split-controls");
  const splitCountVal = document.getElementById("split-count-val");
  const splitDecBtn = document.getElementById("split-dec-btn");
  const splitIncBtn = document.getElementById("split-inc-btn");
  const splitWithInput = document.getElementById("split-with-input");

  let splitCount = 2;

  // Set expense date from URL parameter (?date=YYYY-MM-DD) or default to today
  const urlParams = new URLSearchParams(window.location.search);
  const paramDate = urlParams.get("date");
  if (dateInput) {
    if (paramDate && /^\d{4}-\d{2}-\d{2}$/.test(paramDate)) {
      dateInput.value = paramDate;
    } else if (!dateInput.value) {
      const todayStr = new Date().toISOString().slice(0, 10);
      dateInput.value = todayStr;
    }
  }

  function markInteractionStart() {
    if (!logInteractionStartTime) {
      logInteractionStartTime = performance.now();
    }
  }

  if (amountInput) {
    amountInput.addEventListener("focus", markInteractionStart);
    amountInput.addEventListener("input", () => {
      updateSplitPreview();
      updateSubmitButtonImpact();
    });
  }
  if (noteInput) noteInput.addEventListener("focus", markInteractionStart);

  setupQuickBumps();
  setupInstantSaveToggle();

  if (splitToggle && splitControls) {
    splitToggle.addEventListener("change", () => {
      markInteractionStart();
      splitControls.style.display = splitToggle.checked ? "flex" : "none";
      updateSplitPreview();
    });
  }

  if (splitIncBtn && splitDecBtn && splitCountVal) {
    splitIncBtn.addEventListener("click", () => {
      markInteractionStart();
      splitCount = Math.min(10, splitCount + 1);
      splitCountVal.textContent = splitCount;
      updateSplitPreview();
    });

    splitDecBtn.addEventListener("click", () => {
      markInteractionStart();
      splitCount = Math.max(2, splitCount - 1);
      splitCountVal.textContent = splitCount;
      updateSplitPreview();
    });
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const rawAmt = parseFloat(amountInput.value);

    if (!rawAmt || rawAmt <= 0) {
      showToast("Please enter an amount greater than zero.", "error");
      if (amountInput) amountInput.focus();
      return;
    }

    const category = form.querySelector('input[name="category"]:checked')?.value || userCategoriesCache[0]?.name || "Food";
    const moodTag = form.querySelector('input[name="mood_tag"]:checked')?.value || "Essential";
    const isSplit = splitToggle ? splitToggle.checked : false;
    const note = noteInput ? noteInput.value.trim() : "";
    const expenseDate = dateInput ? dateInput.value : null;
    const splitWith = splitWithInput ? splitWithInput.value.trim() : "";

    const payload = {
      amount: rawAmt,
      category: category,
      mood_tag: moodTag,
      is_split: isSplit,
      split_count: isSplit ? splitCount : 1,
      split_with: splitWith,
      note: note,
      expense_date: expenseDate
    };

    try {
      const res = await fetch("/api/expenses", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.error || "Failed to log expense");
      }

      const durationSec = logInteractionStartTime
        ? Math.max(0.6, ((performance.now() - logInteractionStartTime) / 1000)).toFixed(1)
        : "1.4";

      logInteractionStartTime = null;

      showToast(`Saved in ${durationSec}s. Recorded to ledger.`, "success");

      form.reset();
      if (dateInput) dateInput.value = new Date().toISOString().slice(0, 10);
      if (splitControls) splitControls.style.display = "none";
      const splitPreviewText = document.getElementById("split-preview-text");
      if (splitPreviewText) splitPreviewText.textContent = "";

      const defaultCat = form.querySelector('input[name="category"][value="Food"]') || form.querySelector('input[name="category"]');
      if (defaultCat) defaultCat.checked = true;
      const defaultMood = form.querySelector('input[name="mood_tag"][value="Essential"]');
      if (defaultMood) defaultMood.checked = true;

      updateSubmitButtonImpact();

      // Update active page immediately
      if (document.getElementById("live-safe-today-val")) {
        fetchLiveTodayData();
      }
      if (document.getElementById("safe-today-val")) {
        fetchDashboardData();
        loadInsightsData();
      }
    } catch (err) {
      showToast(err.message, "error");
    }
  });
}

async function fetchLiveTodayData() {
  const safeEl = document.getElementById("live-safe-today-val");
  if (!safeEl) return;

  try {
    const [dashRes, expRes] = await Promise.all([
      fetch("/api/dashboard"),
      fetch("/api/expenses?range=today&limit=50")
    ]);

    if (dashRes.ok) {
      const dashData = await dashRes.json();
      const metrics = dashData.metrics;
      if (metrics) {
        currentSafeToSpendToday = metrics.safe_to_spend_today;
        const spentEl = document.getElementById("live-spent-today-val");
        const coachMsgEl = document.getElementById("live-coach-message");
        const coachBoxEl = document.getElementById("live-coach-box");
        const streakEl = document.getElementById("streak-val");

        safeEl.textContent = metrics.safe_to_spend_today.toFixed(2);
        if (spentEl) spentEl.textContent = `₹${metrics.spent_today.toFixed(2)}`;
        if (streakEl) streakEl.textContent = `${metrics.streak} day streak`;

        if (coachMsgEl && coachBoxEl) {
          coachMsgEl.textContent = metrics.coach_message;
          if (metrics.status_tone === "caution") {
            coachBoxEl.classList.add("caution-tone");
          } else {
            coachBoxEl.classList.remove("caution-tone");
          }
        }

        updateSubmitButtonImpact();
      }
    }

    if (expRes.ok) {
      const expData = await expRes.json();
      renderTodayExpenses(expData.expenses || []);
    }
  } catch (err) {
    console.error("fetchLiveTodayData error:", err);
  }
}

function renderTodayExpenses(expenses) {
  todayExpensesCache = expenses || [];
  const container = document.getElementById("today-expenses-container");
  const emptyState = document.getElementById("today-empty-state");
  const countBadge = document.getElementById("today-count-badge");
  if (!container) return;

  if (countBadge) countBadge.textContent = `${todayExpensesCache.length} entr${todayExpensesCache.length === 1 ? 'y' : 'ies'}`;

  if (!todayExpensesCache || todayExpensesCache.length === 0) {
    container.innerHTML = "";
    if (emptyState) emptyState.style.display = "block";
    if (window.lucide) window.lucide.createIcons();
    return;
  }

  if (emptyState) emptyState.style.display = "none";

  container.innerHTML = todayExpensesCache.map(exp => {
    const catObj = userCategoriesCache.find(c => c.name.toLowerCase() === exp.category.toLowerCase());
    const iconName = catObj?.icon || "tag";
    const displayNote = exp.note ? exp.note : exp.category;
    const splitTag = exp.is_split ? `<span class="tag-split">÷ ${exp.split_count}</span>` : "";

    return `
      <div class="ledger-item" style="padding: 10px 0;">
        <div class="ledger-left">
          <div class="ledger-icon-box" style="width: 32px; height: 32px;">
            <i data-lucide="${iconName}" class="lucide-icon" style="width: 14px; height: 14px;"></i>
          </div>
          <div class="ledger-desc-col">
            <div class="ledger-title" style="font-size: 0.875rem;">${displayNote}</div>
            <div class="ledger-meta" style="font-size: 0.6875rem;">
              <span>${exp.category}</span>
              <span>•</span>
              <span>${exp.mood_tag}</span>
              ${splitTag}
            </div>
          </div>
        </div>
        <div class="ledger-right">
          <span class="ledger-amount tnum" style="font-size: 0.9375rem;">₹${parseFloat(exp.amount).toFixed(2)}</span>
          <button type="button" class="btn-table-action edit-today-btn" data-id="${exp.id}" title="Edit entry" aria-label="Edit entry">
            <i data-lucide="pencil" style="width: 13px; height: 13px;"></i>
          </button>
          <button type="button" class="btn-table-action delete delete-today-btn" data-id="${exp.id}" title="Delete entry" aria-label="Delete entry">
            <i data-lucide="trash-2" style="width: 13px; height: 13px;"></i>
          </button>
        </div>
      </div>
    `;
  }).join("");

  if (window.lucide) window.lucide.createIcons();

  container.querySelectorAll(".edit-today-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const id = parseInt(btn.getAttribute("data-id"), 10);
      const item = todayExpensesCache.find(x => x.id === id);
      if (item && window.openSharedEditModal) {
        window.openSharedEditModal(item, () => {
          fetchLiveTodayData();
        });
      }
    });
  });

  container.querySelectorAll(".delete-today-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const id = parseInt(btn.getAttribute("data-id"), 10);
      handleDeleteTodayExpense(id);
    });
  });
}

window.handleDeleteTodayExpense = async function(id) {
  try {
    const res = await fetch(`/api/expenses/${id}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Could not delete expense");
    showToast("Expense removed.", "info", {
      label: "Undo",
      callback: async () => {
        await fetch("/api/expenses/restore", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ expense_id: id })
        });
        showToast("Expense restored.", "success");
        fetchLiveTodayData();
      }
    });
    fetchLiveTodayData();
  } catch (err) {
    showToast(err.message, "error");
  }
};

// =========================================================================
// Transactions Page Engine (Live Filters, Edit Modal, 5-Sec Undo)
// =========================================================================

function setupTransactionsPage() {
  const tableBody = document.getElementById("txTableBody");
  if (!tableBody) return; // Not on /transactions

  let rawExpenses = [];
  let currentRange = "all";
  let currentCategory = "all";
  let currentMood = "all";
  let currentSearch = "";

  const countBadge = document.getElementById("txCountBadge");
  const filteredTotal = document.getElementById("txFilteredTotal");
  const emptyState = document.getElementById("txEmptyState");
  const searchInput = document.getElementById("txSearchInput");

  window.loadTransactions = async function() {
    try {
      const res = await fetch(`/api/expenses?range=${currentRange}&limit=200`);
      if (!res.ok) throw new Error("Could not load transactions");
      const data = await res.json();
      rawExpenses = data.expenses || [];
      applyAndRender();
    } catch (err) {
      console.error(err);
      showToast("Could not load transactions ledger", "error");
    }
  };

  function applyAndRender() {
    let filtered = rawExpenses;

    if (currentCategory !== "all") {
      filtered = filtered.filter(x => x.category === currentCategory);
    }

    if (currentMood !== "all") {
      filtered = filtered.filter(x => x.mood_tag === currentMood);
    }

    if (currentSearch) {
      const q = currentSearch.toLowerCase();
      filtered = filtered.filter(x => {
        const noteMatch = (x.note || "").toLowerCase().includes(q);
        const catMatch = (x.category || "").toLowerCase().includes(q);
        const splitMatch = (x.split_with || "").toLowerCase().includes(q);
        return noteMatch || catMatch || splitMatch;
      });
    }

    // Update Counts & Totals
    const sumAmt = filtered.reduce((acc, curr) => acc + parseFloat(curr.amount || 0), 0);
    if (countBadge) countBadge.textContent = `${filtered.length} entries`;
    if (filteredTotal) filteredTotal.textContent = `Total: ₹${sumAmt.toFixed(2)}`;

    renderTableRows(filtered);
  }

  const categoryIcons = {
    "Food": "utensils",
    "Travel": "car",
    "Hostel/PG": "home",
    "Fun": "party-popper",
    "Misc": "more-horizontal"
  };

  function renderTableRows(expenses) {
    if (!expenses || expenses.length === 0) {
      tableBody.innerHTML = "";
      if (emptyState) emptyState.style.display = "block";
      if (window.lucide) window.lucide.createIcons();
      return;
    }

    if (emptyState) emptyState.style.display = "none";

    tableBody.innerHTML = expenses.map(exp => {
      const iconName = categoryIcons[exp.category] || "tag";
      const dateStr = exp.expense_date || (exp.created_at ? exp.created_at.slice(0, 10) : "");
      const displayNote = exp.note ? exp.note : `<span style="color:var(--ink-muted); font-style:italic;">${exp.category}</span>`;
      
      let splitTag = `<span style="color:var(--ink-muted); font-size:0.75rem;">Solo</span>`;
      if (exp.is_split) {
        const statusText = exp.split_settled ? "Settled" : "Pending";
        splitTag = `
          <span class="tag-split" style="font-size: 0.6875rem;">
            ÷ ${exp.split_count} (${statusText})
          </span>
        `;
      }

      return `
        <tr data-id="${exp.id}">
          <td class="tnum" style="font-size: 0.8125rem; color: var(--ink-muted);">${dateStr}</td>
          <td>
            <div style="font-weight: 700; color: var(--ink-primary);">${displayNote}</div>
            ${exp.split_with ? `<div style="font-size: 0.6875rem; color: var(--ink-muted);">With: ${exp.split_with}</div>` : ""}
          </td>
          <td>
            <span class="table-tag" style="background-color: var(--bg-subtle);">
              <i data-lucide="${iconName}" style="width: 12px; height: 12px;"></i>
              <span>${exp.category}</span>
            </span>
          </td>
          <td>
            <span class="table-tag" style="background-color: var(--bg-subtle);">
              <span>${exp.mood_tag}</span>
            </span>
          </td>
          <td>${splitTag}</td>
          <td class="tnum" style="text-align: right; font-weight: 800; font-size: 0.9375rem;">
            ₹${parseFloat(exp.amount).toFixed(2)}
          </td>
          <td style="text-align: right;">
            <div style="display: inline-flex; gap: 4px;">
              <button type="button" class="btn-table-action edit-tx-btn" data-id="${exp.id}" title="Edit transaction" aria-label="Edit transaction">
                <i data-lucide="pencil" style="width: 14px; height: 14px;"></i>
              </button>
              <button type="button" class="btn-table-action delete delete-tx-btn" data-id="${exp.id}" title="Delete transaction" aria-label="Delete transaction">
                <i data-lucide="trash-2" style="width: 14px; height: 14px;"></i>
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join("");

    if (window.lucide) window.lucide.createIcons();

    // Attach row action listeners
    tableBody.querySelectorAll(".delete-tx-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const id = parseInt(btn.getAttribute("data-id"), 10);
        handleDeleteWithUndo(id);
      });
    });

    tableBody.querySelectorAll(".edit-tx-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const id = parseInt(btn.getAttribute("data-id"), 10);
        const item = rawExpenses.find(x => x.id === id);
        if (item) openEditModal(item);
      });
    });
  }

  // 5-Second Undo Delete
  async function handleDeleteWithUndo(expenseId) {
    try {
      const res = await fetch(`/api/expenses/${expenseId}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Could not delete expense");

      rawExpenses = rawExpenses.filter(x => x.id !== expenseId);
      applyAndRender();

      showToast("Expense removed from ledger.", "info", {
        label: "Undo",
        callback: async () => {
          try {
            const restoreRes = await fetch("/api/expenses/restore", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ expense_id: expenseId })
            });
            if (!restoreRes.ok) throw new Error("Undo failed");
            showToast("Expense restored.", "success");
            window.loadTransactions();
          } catch (e) {
            showToast("Could not restore expense.", "error");
          }
        }
      });
    } catch (err) {
      showToast(err.message, "error");
    }
  }

  // Edit Expense Modal
  const editModal = document.getElementById("editExpenseModal");
  const editForm = document.getElementById("editExpenseForm");
  const closeEditBtn = document.getElementById("closeEditModalBtn");
  const cancelEditBtn = document.getElementById("cancelEditModalBtn");
  const editSplitToggle = document.getElementById("editSplitToggle");
  const editSplitControls = document.getElementById("editSplitControls");
  const editSplitCountVal = document.getElementById("editSplitCountVal");
  const editSplitDecBtn = document.getElementById("editSplitDecBtn");
  const editSplitIncBtn = document.getElementById("editSplitIncBtn");

  let editSplitCount = 2;

  function openEditModal(item) {
    if (!editModal) return;
    document.getElementById("editExpenseId").value = item.id;
    document.getElementById("editAmount").value = item.amount;
    document.getElementById("editDate").value = item.expense_date || (item.created_at ? item.created_at.slice(0, 10) : "");
    document.getElementById("editNote").value = item.note || "";
    document.getElementById("editCategory").value = item.category;
    document.getElementById("editMood").value = item.mood_tag;

    if (editSplitToggle && editSplitControls) {
      editSplitToggle.checked = !!item.is_split;
      editSplitControls.style.display = item.is_split ? "flex" : "none";
      editSplitCount = item.split_count || 2;
      if (editSplitCountVal) editSplitCountVal.textContent = editSplitCount;
      const splitWithEl = document.getElementById("editSplitWith");
      if (splitWithEl) splitWithEl.value = item.split_with || "";
    }

    editModal.classList.add("open");
  }

  function closeEditModal() {
    if (editModal) editModal.classList.remove("open");
  }

  if (closeEditBtn) closeEditBtn.addEventListener("click", closeEditModal);
  if (cancelEditBtn) cancelEditBtn.addEventListener("click", closeEditModal);

  if (editSplitToggle && editSplitControls) {
    editSplitToggle.addEventListener("change", () => {
      editSplitControls.style.display = editSplitToggle.checked ? "flex" : "none";
    });
  }

  if (editSplitIncBtn && editSplitDecBtn && editSplitCountVal) {
    editSplitIncBtn.addEventListener("click", () => {
      editSplitCount = Math.min(10, editSplitCount + 1);
      editSplitCountVal.textContent = editSplitCount;
    });
    editSplitDecBtn.addEventListener("click", () => {
      editSplitCount = Math.max(2, editSplitCount - 1);
      editSplitCountVal.textContent = editSplitCount;
    });
  }

  if (editForm) {
    editForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const id = document.getElementById("editExpenseId").value;
      const rawAmt = parseFloat(document.getElementById("editAmount").value);
      const dateVal = document.getElementById("editDate").value;
      const noteVal = document.getElementById("editNote").value.trim();
      const catVal = document.getElementById("editCategory").value;
      const moodVal = document.getElementById("editMood").value;
      const isSplit = editSplitToggle ? editSplitToggle.checked : false;
      const splitWith = document.getElementById("editSplitWith")?.value.trim() || "";

      if (!rawAmt || rawAmt <= 0) {
        showToast("Amount must be greater than zero.", "error");
        return;
      }

      const payload = {
        amount: rawAmt,
        expense_date: dateVal,
        note: noteVal,
        category: catVal,
        mood_tag: moodVal,
        is_split: isSplit,
        split_count: isSplit ? editSplitCount : 1,
        split_with: splitWith
      };

      try {
        const res = await fetch(`/api/expenses/${id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });

        if (!res.ok) {
          const errData = await res.json();
          throw new Error(errData.error || "Failed to update expense");
        }

        showToast("Transaction updated.", "success");
        closeEditModal();
        window.loadTransactions();
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  }

  // Filter Pill Listeners
  const rangePills = document.querySelectorAll("#txRangePills .tx-pill");
  rangePills.forEach(pill => {
    pill.addEventListener("click", () => {
      rangePills.forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      currentRange = pill.getAttribute("data-range") || "all";
      window.loadTransactions();
    });
  });

  const catPills = document.querySelectorAll("#txCatPills .tx-pill");
  catPills.forEach(pill => {
    pill.addEventListener("click", () => {
      catPills.forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      currentCategory = pill.getAttribute("data-category") || "all";
      applyAndRender();
    });
  });

  const moodPills = document.querySelectorAll("#txMoodPills .tx-pill");
  moodPills.forEach(pill => {
    pill.addEventListener("click", () => {
      moodPills.forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      currentMood = pill.getAttribute("data-mood") || "all";
      applyAndRender();
    });
  });

  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      currentSearch = e.target.value.trim();
      applyAndRender();
    });
  }

  window.loadTransactions();
}

// =========================================================================
// Hostel Splits & Recurring Bills Engine (/splits-bills)
// =========================================================================

function setupSplitsBillsPage() {
  const pendingContainer = document.getElementById("pendingSplitsList");
  if (!pendingContainer) return; // Not on /splits-bills

  const emptyState = document.getElementById("pendingSplitsEmpty");
  const settledContainer = document.getElementById("settledSplitsList");
  const settledCountEl = document.getElementById("settledSplitsCount");
  const headerPendingOwed = document.getElementById("headerPendingOwed");
  const recurringContainer = document.getElementById("recurringBillsList");
  const recurringCountEl = document.getElementById("recurringBillsCount");
  const addBillForm = document.getElementById("addRecurringForm");

  window.loadSplitsBills = async function() {
    try {
      const res = await fetch("/api/splits-bills");
      if (!res.ok) throw new Error("Could not load splits and bills data");
      const data = await res.json();
      renderSplitsBills(data);
    } catch (err) {
      console.error(err);
      showToast("Could not load splits and bills", "error");
    }
  };

  function renderSplitsBills(data) {
    if (headerPendingOwed) {
      headerPendingOwed.textContent = `₹${(data.pending_total || 0).toFixed(2)}`;
    }

    // Pending Splits
    const pending = data.pending_splits || [];
    if (pending.length === 0) {
      pendingContainer.innerHTML = "";
      if (emptyState) emptyState.style.display = "block";
    } else {
      if (emptyState) emptyState.style.display = "none";
      pendingContainer.innerHTML = pending.map(exp => {
        const friend = exp.split_with || "Roommate / Friend";
        const dateStr = exp.expense_date || (exp.created_at ? exp.created_at.slice(0, 10) : "");
        const owedAmt = exp.owed_amount ? parseFloat(exp.owed_amount) : (parseFloat(exp.amount) / exp.split_count);

        return `
          <div class="split-card-item">
            <div class="split-detail-info">
              <div class="split-target-friend">${friend}</div>
              <div class="split-context-meta">
                <span>${exp.note || exp.category}</span>
                <span>•</span>
                <span>Total bill: ₹${parseFloat(exp.amount).toFixed(2)} (÷ ${exp.split_count})</span>
                <span>•</span>
                <span class="tnum">${dateStr}</span>
              </div>
            </div>
            <div class="split-action-col">
              <div class="split-owed-badge tnum">+₹${owedAmt.toFixed(2)}</div>
              <button type="button" class="btn-settle-action" onclick="handleSettleSplit(${exp.id})">
                <i data-lucide="check" style="width: 13px; height: 13px; stroke: #FFFFFF;"></i>
                <span>Mark Settled</span>
              </button>
            </div>
          </div>
        `;
      }).join("");
    }

    // Settled Splits History
    const settled = data.settled_splits || [];
    if (settledCountEl) settledCountEl.textContent = settled.length;

    if (settledContainer) {
      if (settled.length === 0) {
        settledContainer.innerHTML = `<div style="font-size:0.75rem; color:var(--ink-muted); padding: 8px 0;">No settled history yet.</div>`;
      } else {
        settledContainer.innerHTML = settled.map(exp => {
          const friend = exp.split_with || "Friend";
          const owedAmt = exp.owed_amount ? parseFloat(exp.owed_amount) : (parseFloat(exp.amount) / exp.split_count);
          return `
            <div style="display:flex; justify-content:space-between; align-items:center; padding: 6px 0; border-bottom: 1px solid var(--border-hairline); font-size: 0.8125rem;">
              <div>
                <span style="font-weight: 700; color: var(--ink-primary);">${friend}</span>
                <span style="color: var(--ink-muted); margin-left: 6px;">(${exp.note || exp.category})</span>
              </div>
              <div style="display:flex; align-items:center; gap: 8px;">
                <span class="tnum" style="color: var(--ink-secondary); font-weight: 600;">₹${owedAmt.toFixed(2)}</span>
                <span style="font-size: 0.6875rem; color: var(--brand-forest); font-weight: 700; display: inline-flex; align-items: center; gap: 2px;">
                  <i data-lucide="check-circle" style="width: 12px; height: 12px;"></i> Settled
                </span>
              </div>
            </div>
          `;
        }).join("");
      }
    }

    // Fixed Monthly Bills
    const bills = data.recurring_bills || [];
    if (recurringCountEl) recurringCountEl.textContent = `${bills.length} bills`;

    if (recurringContainer) {
      if (bills.length === 0) {
        recurringContainer.innerHTML = `<div style="font-size:0.75rem; color:var(--ink-muted); padding: 12px 0;">No recurring bill templates saved yet. Add your PG rent or Wi-Fi above.</div>`;
      } else {
        recurringContainer.innerHTML = bills.map(bill => {
          const currentMonthStr = new Date().toISOString().slice(0, 7);
          const isLogged = bill.last_logged_month === currentMonthStr;

          return `
            <div class="recurring-card-item">
              <div>
                <div class="recurring-title">${bill.title}</div>
                <div class="recurring-meta">
                  <span>${bill.category}</span>
                  <span>•</span>
                  <span class="tnum" style="font-weight: 700; color: var(--ink-primary);">₹${parseFloat(bill.amount).toFixed(2)} / month</span>
                </div>
              </div>
              <div class="recurring-actions">
                ${isLogged ? `
                  <button type="button" class="btn-log-bill logged" disabled>
                    <i data-lucide="check" style="width: 12px; height: 12px;"></i>
                    <span>Logged</span>
                  </button>
                ` : `
                  <button type="button" class="btn-log-bill" onclick="handleLogRecurringBill(${bill.id})">
                    <i data-lucide="zap" style="width: 12px; height: 12px;"></i>
                    <span>Log Month</span>
                  </button>
                `}
                <button type="button" class="btn-table-action delete" onclick="handleDeleteRecurringBill(${bill.id})" title="Delete template">
                  <i data-lucide="trash-2" style="width: 14px; height: 14px;"></i>
                </button>
              </div>
            </div>
          `;
        }).join("");
      }
    }

    if (window.lucide) window.lucide.createIcons();
  }

  window.handleSettleSplit = async function(expenseId) {
    try {
      const res = await fetch(`/api/expenses/${expenseId}/settle`, { method: "POST" });
      if (!res.ok) throw new Error("Could not settle split");
      showToast("Split marked as settled.", "success");
      window.loadSplitsBills();
    } catch (err) {
      showToast(err.message, "error");
    }
  };

  window.handleLogRecurringBill = async function(billId) {
    try {
      const res = await fetch(`/api/recurring/${billId}/log`, { method: "POST" });
      if (!res.ok) {
        const d = await res.json();
        throw new Error(d.error || "Could not log bill");
      }
      showToast("Fixed bill logged to active expenses.", "success");
      window.loadSplitsBills();
    } catch (err) {
      showToast(err.message, "error");
    }
  };

  window.handleDeleteRecurringBill = async function(billId) {
    if (!confirm("Delete this recurring bill template?")) return;
    try {
      const res = await fetch(`/api/recurring/${billId}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Could not delete bill template");
      showToast("Bill template removed.", "info");
      window.loadSplitsBills();
    } catch (err) {
      showToast(err.message, "error");
    }
  };

  if (addBillForm) {
    addBillForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const title = document.getElementById("billTitle")?.value.trim();
      const amt = parseFloat(document.getElementById("billAmount")?.value);
      const cat = document.getElementById("billCategory")?.value || "Hostel/PG";

      if (!title || !amt || amt <= 0) {
        showToast("Enter a valid bill title and amount.", "error");
        return;
      }

      try {
        const res = await fetch("/api/recurring", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title, amount: amt, category: cat })
        });
        if (!res.ok) throw new Error("Could not save bill template");
        showToast("Fixed bill template saved.", "success");
        addBillForm.reset();
        window.loadSplitsBills();
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  }

  window.loadSplitsBills();
}

// =========================================================================
// 48-Hour Impulse Cooldown Wishlist (/cooldown)
// =========================================================================

function setupCooldownWishlist() {
  const form = document.getElementById("cooldown-form");
  const itemNameInput = document.getElementById("cooldown-name");
  const itemAmtInput = document.getElementById("cooldown-amount");
  const itemsContainer = document.getElementById("cooldown-items-list");
  const totalSavedEl = document.getElementById("cooldown-total-saved");

  if (!itemsContainer && !form) return;

  async function loadCooldownItems() {
    if (!itemsContainer) return;
    try {
      const res = await fetch("/api/cooldown");
      if (!res.ok) throw new Error("Could not load cooldown items");
      const data = await res.json();

      if (totalSavedEl) {
        totalSavedEl.textContent = `₹${data.total_saved.toLocaleString()}`;
      }

      renderCooldownItems(data.items);
    } catch (err) {
      console.error(err);
    }
  }

  function renderCooldownItems(items) {
    if (!itemsContainer) return;
    if (!items || items.length === 0) {
      itemsContainer.innerHTML = `
        <div style="text-align: center; padding: 32px 16px; color: var(--ink-muted);">
          <i data-lucide="clock" style="width: 28px; height: 28px; stroke: var(--border-strong); margin-bottom: 6px;"></i>
          <div style="font-size: 0.875rem; font-weight: 700; color: var(--ink-primary); margin-bottom: 2px;">Holding Tank Empty</div>
          <div style="font-size: 0.75rem;">Park non-essential desires for 48 hours to prevent impulse regrets.</div>
        </div>
      `;
      if (window.lucide) window.lucide.createIcons();
      return;
    }

    itemsContainer.innerHTML = items.map(item => {
      const unlockTime = new Date(item.unlock_at).getTime();
      const now = Date.now();
      const isUnlocked = now >= unlockTime;

      let statusBadge = "";
      let actionButtons = "";

      if (item.status === "skipped") {
        statusBadge = `<span class="tag-split" style="background:var(--brand-sage-bg); color:var(--brand-sage-ink);">Saved ₹${parseFloat(item.amount).toFixed(2)}</span>`;
      } else if (item.status === "bought") {
        statusBadge = `<span class="tag-split" style="background:var(--bg-subtle); color:var(--ink-muted);">Logged to Fun</span>`;
      } else {
        const remainingMs = Math.max(0, unlockTime - now);
        const hours = Math.floor(remainingMs / (1000 * 60 * 60));
        const mins = Math.floor((remainingMs % (1000 * 60 * 60)) / (1000 * 60));

        statusBadge = `
          <div class="streak-pill ${isUnlocked ? 'caution-tone' : ''}" style="padding: 3px 8px; font-size: 0.75rem;">
            <i data-lucide="clock" style="width: 12px; height: 12px;"></i>
            <span>${isUnlocked ? '48h elapsed • Decide now' : `${hours}h ${mins}m left`}</span>
          </div>
        `;

        actionButtons = `
          <div style="display:flex; gap:6px; margin-top:10px;">
            <button type="button" class="btn-forest-primary" style="flex:1; height:34px; font-size:0.75rem;" onclick="handleCooldownAction(${item.id}, 'skipped')">
              <i data-lucide="check" style="width: 12px; height: 12px;"></i>
              <span>Skipped It</span>
            </button>
            <button type="button" class="preset-chip-btn" style="flex:1; height:34px; font-size:0.75rem;" onclick="handleCooldownAction(${item.id}, 'bought')">
              <i data-lucide="shopping-bag" style="width: 12px; height: 12px;"></i>
              <span>Still Want It</span>
            </button>
          </div>
        `;
      }

      return `
        <div class="fintech-card" style="padding: 14px 16px; margin-bottom: 8px;">
          <div style="display:flex; justify-content:space-between; align-items:flex-start;">
            <div>
              <div style="font-size: 0.9375rem; font-weight: 700; color: var(--ink-primary);">${item.item_name}</div>
              <div style="margin-top: 4px;">${statusBadge}</div>
            </div>
            <div class="hero-amount tnum" style="font-size: 1.15rem; font-weight: 800;">₹${parseFloat(item.amount).toFixed(2)}</div>
          </div>
          ${actionButtons}
        </div>
      `;
    }).join("");

    if (window.lucide) {
      window.lucide.createIcons();
    }
  }

  window.handleCooldownAction = async function(id, action) {
    try {
      const res = await fetch(`/api/cooldown/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: action })
      });
      if (!res.ok) throw new Error("Could not update item");
      if (action === "skipped") {
        showToast("Impulse buy skipped. Rupee savings recorded.", "success");
      } else {
        showToast("Logged to monthly ledger under Fun • Impulse.", "info");
      }
      loadCooldownItems();
    } catch (err) {
      showToast(err.message, "error");
    }
  };

  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const name = itemNameInput?.value.trim();
      const amt = parseFloat(itemAmtInput?.value);

      if (!name || !amt || amt <= 0) {
        showToast("Please enter an item name and amount.", "error");
        return;
      }

      try {
        const res = await fetch("/api/cooldown", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ item_name: name, amount: amt })
        });
        if (!res.ok) throw new Error("Could not add to cooldown");
        showToast("Parked for 48 hours in holding tank.", "success");
        form.reset();
        loadCooldownItems();
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  }

  loadCooldownItems();
}

// =========================================================================
// SpendCalm Buddy Drawer (Editorial Slide-Over AI)
// =========================================================================

function setupAIBuddy() {
  const fab = document.getElementById("ai-buddy-fab");
  const headerBtn = document.getElementById("header-ai-btn");
  const drawer = document.getElementById("ai-drawer");
  const overlay = document.getElementById("ai-drawer-overlay");
  const closeBtn = document.getElementById("ai-drawer-close");
  const clearChatBtn = document.getElementById("clearChatBtn");
  const chatForm = document.getElementById("ai-chat-form");
  const chatInput = document.getElementById("ai-chat-input");
  const chatBody = document.getElementById("ai-chat-body");
  const voiceBtn = document.getElementById("ai-voice-btn");
  const chipBtns = document.querySelectorAll(".chip-prompt-btn");
  const statusIndicator = document.getElementById("ai-status-indicator");
  const statusText = document.getElementById("ai-status-text");

  if (!drawer) return;

  const chatHistory = [];

  function formatModelLabel(modelName) {
    if (!modelName) return "Gemini Connected";
    const raw = modelName.replace(/^models\//, "").trim();
    // Handle specific common names nicely
    const parts = raw.split(/[-_]/).map(w => {
      if (/^\d+(\.\d+)?$/.test(w)) return w;
      return w.charAt(0).toUpperCase() + w.slice(1);
    });
    const label = parts.join(" ");
    return label.startsWith("Gemini") ? label : `Gemini ${label}`;
  }

  async function refreshAIStatus() {
    if (!statusIndicator || !statusText) return;
    try {
      const res = await fetch("/api/ai-status");
      if (!res.ok) throw new Error("Status check failed");
      const data = await res.json();
      const dot = statusIndicator.querySelector(".status-dot");
      if (data.ai_mode === "gemini") {
        if (dot) dot.className = "status-dot online";
        statusText.textContent = formatModelLabel(data.model);
        statusIndicator.setAttribute("title", `Model: ${data.model || "Gemini"}`);
      } else {
        if (dot) dot.className = "status-dot fallback";
        statusText.textContent = "Fallback Mode";
        statusIndicator.setAttribute("title", data.error_hint || "Operating in offline smart fallback mode");
      }
    } catch (e) {
      const dot = statusIndicator ? statusIndicator.querySelector(".status-dot") : null;
      if (dot) dot.className = "status-dot fallback";
      if (statusText) statusText.textContent = "Fallback Mode";
    }
  }

  function openDrawer() {
    drawer.classList.add("open");
    if (overlay) overlay.classList.add("open");
    if (chatInput) chatInput.focus();
    refreshAIStatus();
    if (window.lucide) window.lucide.createIcons();
  }

  function closeDrawer() {
    drawer.classList.remove("open");
    if (overlay) overlay.classList.remove("open");
    if (isRecording) {
      stopVoiceRecording();
    }
  }

  if (fab) fab.addEventListener("click", openDrawer);
  if (headerBtn) headerBtn.addEventListener("click", openDrawer);
  if (closeBtn) closeBtn.addEventListener("click", closeDrawer);
  if (overlay) overlay.addEventListener("click", closeDrawer);

  function appendMessage(sender, text, isVoice = false) {
    if (!chatBody) return;
    const msg = document.createElement("div");
    msg.className = `chat-bubble ${sender}`;
    if (isVoice && sender === "user") {
      msg.innerHTML = `<span style="display:inline-flex; align-items:center; gap:4px; opacity:0.85; font-size:0.75rem; margin-right:6px;"><i data-lucide="mic" style="width:12px; height:12px;"></i> Voice</span>${escapeHtml(text)}`;
    } else {
      msg.textContent = text;
    }
    chatBody.appendChild(msg);
    chatBody.scrollTop = chatBody.scrollHeight;
    if (window.lucide) window.lucide.createIcons();
  }

  function triggerLiveSync(data) {
    const action = data.action || data.intent || data.mode;
    if (action === "log_expense" && data.expense_logged) {
      showToast(`AI logged: ₹${data.expense_logged.amount} (${data.expense_logged.category})`, "success");
    } else if (action === "delete_last_expense" && data.expense_deleted) {
      showToast(`Expense removed: ₹${data.expense_deleted.amount} (${data.expense_deleted.note})`, "info");
    } else if (action === "add_cooldown" && data.cooldown_added) {
      showToast(`Added to 48h Cooldown: ₹${data.cooldown_added.amount} (${data.cooldown_added.item_name})`, "success");
    }

    if (data.expense_logged || data.expense_deleted || data.cooldown_added) {
      if (document.getElementById("safe-today-val")) {
        fetchDashboardData();
        loadInsightsData();
      }
      if (document.getElementById("live-safe-today-val")) {
        fetchLiveTodayData();
      }
      if (document.getElementById("txTableBody") && window.loadTransactions) {
        window.loadTransactions();
      }
      if (document.getElementById("pendingSplitsList") && window.loadSplitsBills) {
        window.loadSplitsBills();
      }
      if (document.getElementById("calendarGrid") && window.loadCalendarMonth) {
        window.loadCalendarMonth();
      }
      if (document.getElementById("cooldown-items-container") && window.loadCooldownItems) {
        window.loadCooldownItems();
      }
    }
  }

  async function sendToAI(userText, isVoice = false) {
    if (!userText.trim()) return;
    appendMessage("user", userText, isVoice);
    chatHistory.push({ role: "user", text: userText });
    if (chatHistory.length > 8) chatHistory.shift();

    if (chatInput) chatInput.value = "";

    const typingId = "ai-typing-placeholder";
    const typingMsg = document.createElement("div");
    typingMsg.id = typingId;
    typingMsg.className = "chat-bubble assistant";
    typingMsg.innerHTML = "<em>Reflecting calmly...</em>";
    if (chatBody) {
      chatBody.appendChild(typingMsg);
      chatBody.scrollTop = chatBody.scrollHeight;
    }

    try {
      const res = await fetch("/api/ai-chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userText,
          history: chatHistory.slice(0, -1)
        })
      });

      const indicator = document.getElementById(typingId);
      if (indicator) indicator.remove();

      if (!res.ok) throw new Error("Could not reach SmartSpend AI");
      const data = await res.json();

      appendMessage("assistant", data.reply);
      chatHistory.push({ role: "assistant", text: data.reply });
      if (chatHistory.length > 8) chatHistory.shift();

      if (data.ai_mode === "gemini") {
        const dot = statusIndicator ? statusIndicator.querySelector(".status-dot") : null;
        if (dot) dot.className = "status-dot online";
        if (statusText) statusText.textContent = `Gemini (${data.model || "Connected"})`;
      } else if (data.ai_mode === "fallback") {
        const dot = statusIndicator ? statusIndicator.querySelector(".status-dot") : null;
        if (dot) dot.className = "status-dot fallback";
        if (statusText) statusText.textContent = "Fallback Mode";
      }

      triggerLiveSync(data);
    } catch (err) {
      const indicator = document.getElementById(typingId);
      if (indicator) indicator.remove();
      appendMessage("assistant", "SmartSpend AI is taking a quick rest. Your 1-tap presets work instantly!");
    }
  }

  // =======================================================================
  // 1-Button Voice Assistant (Real-Time Web Speech API + Gemini Multimodal Fallback)
  // =======================================================================
  const voiceBanner = document.getElementById("voice-active-banner");
  const voiceLabel = document.getElementById("voice-status-label");
  const pageVoiceBtn = document.getElementById("log-page-voice-btn");

  let recognition = null;
  let mediaRecorder = null;
  let audioChunks = [];
  let isRecording = false;
  let mediaStream = null;
  let maxRecordTimer = null;
  let speechDebounceTimer = null;
  let recordedTextBuffer = "";

  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;

  function setVoiceUIActive(active, statusText = "Listening... Speak naturally") {
    isRecording = active;
    if (voiceBtn) {
      if (active) {
        voiceBtn.classList.add("recording");
        voiceBtn.setAttribute("title", "Tap to finish speaking");
      } else {
        voiceBtn.classList.remove("recording");
        voiceBtn.setAttribute("title", "Hold or tap to speak");
      }
    }
    if (voiceBanner) {
      voiceBanner.style.display = active ? "flex" : "none";
    }
    if (voiceLabel) {
      voiceLabel.textContent = statusText;
    }
    if (chatInput) {
      if (active) {
        chatInput.placeholder = "Listening... Speak naturally (e.g. '20 for chai')";
      } else {
        chatInput.placeholder = "Type spend or tap mic to speak...";
      }
    }
    if (window.lucide) window.lucide.createIcons();
  }

  function startVoiceRecording() {
    recordedTextBuffer = "";

    // 1. PRIMARY: Native Web Speech API (real-time, zero latency, en-IN accent tuned)
    if (SpeechRec) {
      try {
        if (!recognition) {
          recognition = new SpeechRec();
          recognition.continuous = false;
          recognition.interimResults = true;
          recognition.lang = "en-IN";

          recognition.onstart = () => {
            setVoiceUIActive(true, "Listening... Speak naturally (e.g. '20 for chai')");
          };

          recognition.onresult = (event) => {
            let interimTranscript = "";
            for (let i = event.resultIndex; i < event.results.length; ++i) {
              const res = event.results[i];
              if (res.isFinal) {
                recordedTextBuffer += res[0].transcript + " ";
              } else {
                interimTranscript += res[0].transcript;
              }
            }
            const currentDisplay = (recordedTextBuffer + interimTranscript).trim();
            if (chatInput && currentDisplay) {
              chatInput.value = currentDisplay;
            }
            if (voiceLabel && currentDisplay) {
              voiceLabel.textContent = `Heard: "${currentDisplay.slice(0, 35)}..."`;
            }

            // Anti-clipping: 1.4s silence debounce to allow natural mid-sentence pauses
            if (speechDebounceTimer) clearTimeout(speechDebounceTimer);
            speechDebounceTimer = setTimeout(() => {
              if (isRecording) {
                stopVoiceRecording();
              }
            }, 1400);
          };

          recognition.onerror = (event) => {
            console.warn("SpeechRecognition error:", event.error);
            if (speechDebounceTimer) clearTimeout(speechDebounceTimer);
            setVoiceUIActive(false);
            if (event.error === "not-allowed") {
              showToast("Microphone access denied. Please allow microphone access.", "error");
            } else if (event.error === "no-speech") {
              showToast("No speech detected. Please speak closer to your mic.", "info");
            } else {
              fallbackMediaRecorder();
            }
          };

          recognition.onend = () => {
            if (speechDebounceTimer) clearTimeout(speechDebounceTimer);
            setVoiceUIActive(false);
            const finalText = (chatInput ? chatInput.value : recordedTextBuffer).trim();
            if (finalText) {
              sendToAI(finalText, true);
            }
          };
        }

        recognition.start();
        return;
      } catch (err) {
        console.warn("Could not start SpeechRecognition, falling back to MediaRecorder:", err);
      }
    }

    // 2. SECONDARY: MediaRecorder audio stream fallback
    fallbackMediaRecorder();
  }

  async function fallbackMediaRecorder() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      showToast("Voice recording is not supported in this browser.", "error");
      if (chatInput) chatInput.focus();
      return;
    }

    try {
      audioChunks = [];
      mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });

      const mimeTypes = ["audio/webm", "audio/ogg", "audio/mp4", "audio/wav"];
      let selectedMime = "";
      for (const mime of mimeTypes) {
        if (MediaRecorder.isTypeSupported(mime)) {
          selectedMime = mime;
          break;
        }
      }

      mediaRecorder = selectedMime ? new MediaRecorder(mediaStream, { mimeType: selectedMime }) : new MediaRecorder(mediaStream);

      mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunks.push(event.data);
        }
      };

      mediaRecorder.onstart = () => {
        setVoiceUIActive(true, "Recording audio... Tap mic when finished");
        if (maxRecordTimer) clearTimeout(maxRecordTimer);
        maxRecordTimer = setTimeout(() => {
          if (isRecording) stopVoiceRecording();
        }, 7000);
      };

      mediaRecorder.onstop = async () => {
        setVoiceUIActive(false);
        if (maxRecordTimer) clearTimeout(maxRecordTimer);

        if (mediaStream) {
          mediaStream.getTracks().forEach((track) => track.stop());
          mediaStream = null;
        }

        if (audioChunks.length === 0) return;

        const rawMime = mediaRecorder.mimeType || "audio/webm";
        const cleanMime = rawMime.split(";")[0].trim().toLowerCase();
        const audioBlob = new Blob(audioChunks, { type: cleanMime });
        await sendVoiceToAI(audioBlob);
      };

      mediaRecorder.start(250);
    } catch (err) {
      console.warn("Microphone access error:", err);
      setVoiceUIActive(false);
      showToast("Microphone access denied or unavailable. Please type your spend.", "error");
      if (chatInput) chatInput.focus();
    }
  }

  function stopVoiceRecording() {
    if (speechDebounceTimer) clearTimeout(speechDebounceTimer);
    if (maxRecordTimer) clearTimeout(maxRecordTimer);
    if (recognition) {
      try {
        recognition.stop();
      } catch (e) {}
    }
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
      try {
        mediaRecorder.stop();
      } catch (e) {}
    }
    setVoiceUIActive(false);
  }

  async function sendVoiceToAI(blob) {
    const typingId = "ai-typing-placeholder";
    const typingMsg = document.createElement("div");
    typingMsg.id = typingId;
    typingMsg.className = "chat-bubble assistant";
    typingMsg.innerHTML = "<em>Analyzing your voice note...</em>";
    if (chatBody) {
      chatBody.appendChild(typingMsg);
      chatBody.scrollTop = chatBody.scrollHeight;
    }

    try {
      const formData = new FormData();
      formData.append("audio", blob, "voice_command.webm");
      formData.append("history", JSON.stringify(chatHistory));

      const res = await fetch("/api/ai-voice", {
        method: "POST",
        body: formData
      });

      const indicator = document.getElementById(typingId);
      if (indicator) indicator.remove();

      if (!res.ok) throw new Error("Could not process voice command");
      const data = await res.json();

      const userText = data.transcript || "Voice command";
      appendMessage("user", userText, true);
      chatHistory.push({ role: "user", text: userText });
      if (chatHistory.length > 8) chatHistory.shift();

      appendMessage("assistant", data.reply);
      chatHistory.push({ role: "assistant", text: data.reply });
      if (chatHistory.length > 8) chatHistory.shift();

      if (data.ai_mode === "gemini") {
        const dot = statusIndicator ? statusIndicator.querySelector(".status-dot") : null;
        if (dot) dot.className = "status-dot online";
        if (statusText) statusText.textContent = `Gemini (${data.model || "Connected"})`;
      } else if (data.ai_mode === "fallback") {
        const dot = statusIndicator ? statusIndicator.querySelector(".status-dot") : null;
        if (dot) dot.className = "status-dot fallback";
        if (statusText) statusText.textContent = "Fallback Mode";
      }

      triggerLiveSync(data);
    } catch (err) {
      const indicator = document.getElementById(typingId);
      if (indicator) indicator.remove();
      appendMessage("assistant", "Could not process the audio clearly. You can also type your spend directly!");
      showToast("Voice command error. Please try typing.", "error");
    }
  }

  if (voiceBtn) {
    voiceBtn.addEventListener("click", () => {
      if (isRecording) {
        stopVoiceRecording();
      } else {
        startVoiceRecording();
      }
    });
  }

  if (pageVoiceBtn) {
    pageVoiceBtn.addEventListener("click", () => {
      openDrawer();
      setTimeout(() => {
        if (!isRecording) startVoiceRecording();
      }, 300);
    });
  }

  function bindChipPrompts() {
    if (!chatBody) return;
    chatBody.querySelectorAll(".chip-prompt-btn").forEach(btn => {
      btn.onclick = () => {
        const prompt = btn.getAttribute("data-prompt") || btn.textContent.trim().replace(/^["']|["']$/g, "");
        sendToAI(prompt);
      };
    });
  }

  if (clearChatBtn) {
    clearChatBtn.addEventListener("click", () => {
      chatHistory.length = 0;
      sessionStorage.removeItem("spendcalm_ai_history");
      if (chatBody) {
        chatBody.innerHTML = `
          <div class="chat-bubble assistant">
            Chat cleared. Tell me what you spent (e.g., '₹40 chai at gate') or ask if a purchase fits today's pace.
          </div>
          <div class="ai-prompt-chips">
            <button type="button" class="chip-prompt-btn" data-prompt="Log ₹30 chai with friends">"Log ₹30 chai with friends"</button>
            <button type="button" class="chip-prompt-btn" data-prompt="Split ₹180 auto with 2 roommates">"Split ₹180 auto with 2 roommates"</button>
            <button type="button" class="chip-prompt-btn" data-prompt="Can I afford a ₹200 treat today?">"Can I afford a ₹200 treat today?"</button>
          </div>
        `;
        bindChipPrompts();
      }
      showToast("Chat cleared", "info");
      if (window.lucide) window.lucide.createIcons();
    });
  }

  if (chatForm) {
    chatForm.addEventListener("submit", (e) => {
      e.preventDefault();
      if (chatInput) sendToAI(chatInput.value);
    });
  }

  bindChipPrompts();

  // Check initial AI connection status
  refreshAIStatus();
}

// =========================================================================
// Monthly Target Budget Modal
// =========================================================================

function setupParticipantModal() {
  const openBtn = document.getElementById("open-participant-modal");
  const mobileOpenBtn = document.getElementById("mobile-open-modal");
  const collapsedBudgetBtn = document.getElementById("collapsedBudgetBtn");
  const modal = document.getElementById("participant-modal");
  const closeBtn = document.getElementById("close-participant-modal");
  const cancelBtn = document.getElementById("modal-cancel-btn");
  const form = document.getElementById("participant-form");
  const codeInput = document.getElementById("modal-participant-code");
  const budgetInput = document.getElementById("modal-monthly-budget");

  function openModal() {
    if (modal) modal.classList.add("open");
    if (budgetInput) {
      budgetInput.focus();
      budgetInput.select();
    }
  }

  function closeModal() {
    if (modal) modal.classList.remove("open");
  }

  if (openBtn) openBtn.addEventListener("click", openModal);
  if (mobileOpenBtn) mobileOpenBtn.addEventListener("click", openModal);
  if (collapsedBudgetBtn) collapsedBudgetBtn.addEventListener("click", openModal);
  if (closeBtn) closeBtn.addEventListener("click", closeModal);
  if (cancelBtn) cancelBtn.addEventListener("click", closeModal);

  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const code = codeInput ? codeInput.value.trim().toUpperCase() : (window.SmartSpendUser?.participant_code || "P01");
      const budget = parseFloat(budgetInput?.value) || 3000;

      if (budget <= 0) {
        showToast("Please enter a valid monthly budget.", "error");
        return;
      }

      try {
        const res = await fetch("/api/session", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ participant_code: code || "P01", monthly_budget: budget })
        });

        if (!res.ok) throw new Error("Could not update monthly budget");
        const data = await res.json();
        window.SpendCalmUser = data.user;
        window.SmartSpendUser = data.user;

        showToast(`Budget updated: ₹${data.user.monthly_budget.toLocaleString()}`, "success");
        closeModal();
        window.location.reload();
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  }
}

// =========================================================================
// Collapsible / Slide-Out Sidebar Engine
// =========================================================================

function setupCollapsibleSidebar() {
  const sidebar = document.querySelector(".app-sidebar") || document.querySelector(".sidebar");
  const collapseBtn = document.getElementById("sidebarCollapseBtn");
  const openBtn = document.getElementById("sidebarOpenBtn");
  const mobileToggle = document.getElementById("mobileSidebarToggle");
  const backdrop = document.getElementById("sidebarBackdrop");
  const navLinks = sidebar ? sidebar.querySelectorAll(".sidebar-nav-item") : [];

  if (!sidebar) return;

  function isDesktop() {
    return window.innerWidth >= 1024;
  }

  function updateCollapseBtnState(isCollapsed) {
    if (!collapseBtn) return;
    if (isCollapsed) {
      collapseBtn.innerHTML = '<i data-lucide="panel-left-open" class="lucide-icon" style="width: 18px; height: 18px;"></i>';
      collapseBtn.setAttribute("title", "Expand sidebar");
      collapseBtn.setAttribute("aria-label", "Expand sidebar");
      collapseBtn.setAttribute("data-tooltip", "Expand sidebar");
    } else {
      collapseBtn.innerHTML = '<i data-lucide="panel-left-close" class="lucide-icon" style="width: 18px; height: 18px;"></i>';
      collapseBtn.setAttribute("title", "Collapse sidebar");
      collapseBtn.setAttribute("aria-label", "Collapse sidebar");
      collapseBtn.setAttribute("data-tooltip", "Collapse sidebar");
    }
    if (window.lucide) {
      window.lucide.createIcons();
    }
  }

  function collapseDesktop() {
    document.body.classList.add("sidebar-collapsed");
    try {
      localStorage.setItem("smartspend_sidebar_collapsed", "true");
    } catch (e) {}
    updateCollapseBtnState(true);
    notifyChartResize();
  }

  function expandDesktop() {
    document.body.classList.remove("sidebar-collapsed");
    try {
      localStorage.setItem("smartspend_sidebar_collapsed", "false");
    } catch (e) {}
    updateCollapseBtnState(false);
    notifyChartResize();
  }

  function toggleDesktop() {
    if (document.body.classList.contains("sidebar-collapsed")) {
      expandDesktop();
    } else {
      collapseDesktop();
    }
  }

  function openMobile() {
    sidebar.classList.add("mobile-open");
    if (backdrop) backdrop.classList.add("active");
    document.body.classList.add("mobile-sidebar-open");
  }

  function closeMobile() {
    sidebar.classList.remove("mobile-open");
    if (backdrop) backdrop.classList.remove("active");
    document.body.classList.remove("mobile-sidebar-open");
  }

  function toggleMobile() {
    if (sidebar.classList.contains("mobile-open")) {
      closeMobile();
    } else {
      openMobile();
    }
  }

  function notifyChartResize() {
    setTimeout(() => {
      window.dispatchEvent(new Event("resize"));
    }, 260);
  }

  // Restore initial state on desktop
  if (isDesktop()) {
    try {
      const saved = localStorage.getItem("smartspend_sidebar_collapsed");
      if (saved === "true") {
        document.body.classList.add("sidebar-collapsed");
        updateCollapseBtnState(true);
      } else {
        document.body.classList.remove("sidebar-collapsed");
        updateCollapseBtnState(false);
      }
    } catch (e) {
      updateCollapseBtnState(document.body.classList.contains("sidebar-collapsed"));
    }
  }

  if (collapseBtn) {
    collapseBtn.addEventListener("click", () => {
      if (isDesktop()) {
        toggleDesktop();
      } else {
        closeMobile();
      }
    });
  }

  if (openBtn) {
    openBtn.addEventListener("click", () => {
      if (isDesktop()) {
        expandDesktop();
      } else {
        openMobile();
      }
    });
  }

  if (mobileToggle) {
    mobileToggle.addEventListener("click", toggleMobile);
  }

  if (backdrop) {
    backdrop.addEventListener("click", closeMobile);
  }

  // Close mobile drawer on navigation link tap
  navLinks.forEach(link => {
    link.addEventListener("click", () => {
      if (!isDesktop()) {
        closeMobile();
      }
    });
  });

  // Keyboard shortcuts: Esc closes mobile drawer, Ctrl/Cmd + B toggles desktop sidebar
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      if (!isDesktop() && sidebar.classList.contains("mobile-open")) {
        closeMobile();
      }
    }

    if ((e.ctrlKey || e.metaKey) && (e.key === "b" || e.key === "B")) {
      const activeTag = document.activeElement ? document.activeElement.tagName.toLowerCase() : "";
      if (activeTag === "input" || activeTag === "textarea" || activeTag === "select") {
        return;
      }
      e.preventDefault();
      if (isDesktop()) {
        toggleDesktop();
      } else {
        toggleMobile();
      }
    }
  });

  // Window resize handler: reset mobile drawer if viewport expands to desktop
  window.addEventListener("resize", () => {
    if (isDesktop()) {
      closeMobile();
    }
  });

  if (window.lucide) {
    window.lucide.createIcons();
  }
}

// =========================================================================
// Application Initialization
// =========================================================================

document.addEventListener("DOMContentLoaded", () => {
  // Common utilities
  setupCollapsibleSidebar();
  setupAIBuddy();
  setupParticipantModal();
  setupKeyboardShortcuts();
  setupSharedEditModal();
  loadUserCategories();

  // Overview Page Engine (Dashboard + Insights Analytics)
  if (document.getElementById("safe-today-val")) {
    fetchDashboardData();
    setupInsightsTabs();
    loadInsightsData();
  }

  // Dedicated Log Expense Page Engine
  if (document.getElementById("live-safe-today-val")) {
    renderPresetsStrip();
    setupPresetCustomizer();
    setupCategoryManager();
    setupRapidLogger();
    fetchLiveTodayData();
  }

  // Transactions Page Engine
  if (document.getElementById("txTableBody")) {
    setupTransactionsPage();
  }

  // Splits & Bills Page Engine
  if (document.getElementById("pendingSplitsList")) {
    setupSplitsBillsPage();
  }

  // Cooldown Page Engine
  if (document.getElementById("cooldown-items-list")) {
    setupCooldownWishlist();
  }

  if (window.lucide) {
    window.lucide.createIcons();
  }
});
