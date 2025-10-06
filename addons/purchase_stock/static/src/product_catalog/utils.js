/** False if PO is not draft, otherwise loads last toggle state from local storage (defaults to false)  */
export function getSuggestToggleState(poState) {
    if (poState == "draft") {
        const toggle = JSON.parse(localStorage.getItem("purchase_stock.suggest_toggle_state"));
        return toggle ?? { isOn: false };
    }
    return { isOn: false };
}
