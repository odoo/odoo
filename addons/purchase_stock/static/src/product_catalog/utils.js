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
    return {
        ...baseContext,
        ...suggestContext,
    };
}

function removeSuggestContext(baseContext, suggestContext) {
    const suggestKeys = new Set([
        ...Object.keys(suggestContext || {}).filter((k) => k != "warehouse_id"),
    ]);
    for (const k of suggestKeys) {
        delete baseContext[k];
    }
    return baseContext;
}

/** False if PO is not draft, otherwise loads last toggle state from local storage (defaults to false)  */
export function getSuggestToggleState(poState) {
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
