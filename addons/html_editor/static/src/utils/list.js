import { removeClass, setTagName } from "./dom";

// Deprecated, use the ListPlugin shared function instead.
export function getListMode(pnode) {
    if (!["UL", "OL"].includes(pnode.tagName)) {
        return;
    }
    if (pnode.tagName === "OL") {
        return "OL";
    }
    return pnode.classList.contains("o_checklist") ? "CL" : "UL";
}

/**
 * Deprecated, use the ListPlugin shared function instead.
 *
 * Switches the list mode of the given list element.
 *
 * @param {HTMLOListElement|HTMLUListElement} list - The list element to switch the mode of.
 * @param {"UL"|"OL"|"CL"} newMode - The new mode to switch to.
 * @param {Object} options
 * @returns {HTMLOListElement|HTMLUListElement} The modified list element.
 */
export function switchListMode(list, newMode) {
    if (getListMode(list) === newMode) {
        return;
    }
    const newTag = newMode === "CL" ? "UL" : newMode;
    const newList = setTagName(list, newTag);
    // Clear list style (@todo @phoenix - why??)
    newList.style.removeProperty("list-style");
    for (const li of newList.children) {
        if (li.style.listStyle !== "none") {
            li.style.listStyle = null;
            if (!li.style.all) {
                li.removeAttribute("style");
            }
        }
    }
    removeClass(newList, "o_checklist");
    if (newMode === "CL") {
        newList.classList.add("o_checklist");
    }
    return newList;
}

/**
 * Deprecated, use the ListPlugin shared function instead.
 *
 * Converts a list element and its nested elements to the given list mode.
 *
 * @see switchListMode
 * @param {HTMLUListElement|HTMLOListElement|HTMLLIElement} node - HTML element
 * representing a list or list item.
 * @param {string} newMode - Target list mode
 * @param {Object} options
 * @returns {HTMLUListElement|HTMLOListElement|HTMLLIElement} node - Modified
 * list element after conversion.
 */
export function convertList(node, newMode) {
    if (!["UL", "OL", "LI"].includes(node.tagName)) {
        return;
    }
    const listMode = getListMode(node);
    if (listMode && newMode !== listMode) {
        node = switchListMode(node, newMode);
    }
    for (const child of node.children) {
        convertList(child, newMode);
    }
    return node;
}
