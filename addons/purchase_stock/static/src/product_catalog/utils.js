const { DateTime } = luxon;

/**
 * Adds / Removes the suggest parameters if suggest feature is ON / OFF
 * @param {Object} baseContext Object to modify in place
 * @param {boolean} suggestOn
 * @param {Object} suggestContext must contain at least based_on key / val pair
 * @returns {Object} base context if suggest is OFF or base + suggest context
 */
export function editSuggestContext(baseContext, suggestOn, suggestContext) {
    if (!suggestOn) {
        return removeSuggestContext(baseContext, suggestContext);
    }
    const [start, limit] = getMonthlyDemandRange(suggestContext.suggest_based_on);
    return {
        ...baseContext,
        ...suggestContext,
        monthly_demand_start: toServerDatetime(start),
        monthly_demand_limit: toServerDatetime(limit),
    };
}

function removeSuggestContext(baseContext, suggestContext) {
    const suggestKeys = new Set([
        ...Object.keys(suggestContext || {}).filter((k) => k != "warehouse_id"),
        "monthly_demand_start",
        "monthly_demand_limit",
    ]);
    for (const k of suggestKeys) {
        delete baseContext[k];
    }
    return baseContext;
}

/** False if PO is not draft, otherwise loads last toggle state from local storage (defaults to false)  */
export function loadSuggestToggleState(poState) {
    if (poState == "draft") {
        const toggle = JSON.parse(localStorage.getItem("purchase_stock.suggest_toggle_state"));
        return toggle ?? { isOn: false };
    }
    return { isOn: false };
}

/** Toggles searchModel filters based on filter name and desired state
 * @param {SearchModel} sm the view's searchModel
 * @param {Array[string]} filterNames eg. "suggested_or_ordered"
 * @param {boolean} turnOn eg. toggles filter "On" if turnOn = true and filter is currently "Off"
 */
export function toggleFilters(sm, filterNames, turnOn) {
    const searchFilters = new Map(Object.values(sm.searchItems).map((i) => [i.name, i]));
    const activeFilters = new Set(sm.query.map((q) => q.searchItemId));

    const toToggle = [];
    for (const name of filterNames) {
        const item = searchFilters.get(name);
        const isOn = activeFilters.has(item.id);
        if ((turnOn && !isOn) || (!turnOn && isOn)) {
            toToggle.push(item.id);
        }
    }

    // Prevent toggleSearchItem from trying to reload with partial domain
    for (let i = 0; i < toToggle.length; i++) {
        const isLast = i === toToggle.length - 1;
        sm.blockNotification = !isLast;
        sm.toggleSearchItem(toToggle[i]);
    }
}

function toServerDatetime(datetime) {
    return new Date(datetime).toISOString().slice(0, 19).replace("T", " ");
}

/** Transform a string to its equivalent date range using hardcoded rules */
export function getMonthlyDemandRange(basedOn) {
    const now = DateTime.now();
    let startDate = now;
    let limitDate = now;

    if (!basedOn || basedOn === "actual_demand" || basedOn === "30_days") {
        startDate = now.minus({ days: 30 });
    } else if (basedOn === "one_week") {
        startDate = now.minus({ weeks: 1 });
    } else if (basedOn === "three_months") {
        startDate = now.minus({ months: 3 });
    } else if (basedOn === "one_year") {
        startDate = now.minus({ years: 1 });
    } else {
        startDate = DateTime.local(now.year - 1, now.month, now.day);

        if (basedOn === "last_year_m_plus_1") {
            startDate = startDate.plus({ months: 1 });
        } else if (basedOn === "last_year_m_plus_2") {
            startDate = startDate.plus({ months: 2 });
        }

        if (basedOn === "last_year_quarter") {
            limitDate = startDate.plus({ months: 3 });
        } else {
            limitDate = startDate.plus({ months: 1 });
        }
    }

    return [startDate, limitDate];
}
