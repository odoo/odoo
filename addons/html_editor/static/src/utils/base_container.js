export const BASE_CONTAINER_CLASS = "o-paragraph";

export const SUPPORTED_BASE_CONTAINER_NAMES = ["P", "DIV"];

/**
 * @param {string} [nodeName] @see SUPPORTED_BASE_CONTAINER_NAMES
 *                 will return the global selector if nodeName is not specified.
 * @returns {string} selector for baseContainers.
 */
export function getBaseContainerSelector(nodeName) {
    if (!nodeName) {
        return baseContainerGlobalSelector;
    }
    nodeName = SUPPORTED_BASE_CONTAINER_NAMES.includes(nodeName) ? nodeName : "P";
    let suffix = "";
    if (nodeName !== "P") {
        suffix = `.${BASE_CONTAINER_CLASS}`;
    }
    return `${nodeName}${suffix}`;
}

export const baseContainerGlobalSelector = SUPPORTED_BASE_CONTAINER_NAMES.map((name) =>
    getBaseContainerSelector(name)
).join(",");

/**
 * Create a new baseContainer element.
 *
 * @param {string} nodeName @see SUPPORTED_BASE_CONTAINER_NAMES
 * @param {Document} [document] Used to create new baseContainer elements.
 *                   For iframes, preferably use the iframe document.
 *                   Fallbacks to the window document if possible and unspecified.
 *                   Has to be specified otherwise.
 * @returns {HTMLElement}
 */
export function createBaseContainer(nodeName, document) {
    if (!document && window) {
        document = window.document;
    }
    nodeName = nodeName && SUPPORTED_BASE_CONTAINER_NAMES.includes(nodeName) ? nodeName : "P";
    const el = document.createElement(nodeName);
    if (nodeName !== "P") {
        el.className = BASE_CONTAINER_CLASS;
    }
    return el;
}
