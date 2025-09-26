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
