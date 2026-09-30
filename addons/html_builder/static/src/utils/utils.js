import { DependencyManager } from "../core/dependency_manager";
import { useSubEnv } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

/**
 * Retrieves the default name corresponding to the edited element (to display it
 * in the sidebar for example).
 *
 * @param {HTMLElement} snippetEl - the edited element
 * @returns {String}
 */
export function getSnippetName(snippetEl) {
    if (snippetEl.dataset.name) {
        return snippetEl.dataset.name;
    }
    if (snippetEl.matches("img")) {
        return _t("Image");
    }
    if (snippetEl.matches(".fa")) {
        return _t("Icon");
    }
    if (snippetEl.matches(".media_iframe_video")) {
        return _t("Video");
    }
    if (snippetEl.parentNode?.matches(".row")) {
        return _t("Column");
    }
    if (snippetEl.matches("#wrapwrap > main")) {
        return _t("Page Options");
    }
    if (snippetEl.matches(".btn")) {
        return _t("Button");
    }
    return _t("Block");
}

/**
 * Checks if the element is visible (= in the viewport).
 *
 * @param {HTMLElement} el
 * @returns {Boolean}
 */
export function isElementInViewport(el) {
    const rect = el.getBoundingClientRect();
    const viewportWidth = window.innerWidth || document.documentElement.clientWidth;
    const viewportHeight = window.innerHeight || document.documentElement.clientHeight;
    return (
        Math.round(rect.top) >= 0 &&
        Math.round(rect.left) >= 0 &&
        Math.round(rect.right) <= viewportWidth &&
        Math.round(rect.bottom) <= viewportHeight
    );
}

/**
 * Checks if the given element is visible in the sense of the jQuery `:visible`
 * selector.
 *
 * @param {HTMLElement} el the element
 * @returns {Boolean}
 */
export function isVisible(el) {
    if (el.offsetHeight > 0 || el.offsetWidth > 0) {
        return true;
    }
    return false;
}

/**
 * Gets all the elements matching an option selector/exclude starting from the
 * root element.
 *
 * @param {HTMLElement} rootEl
 * @param {String} selector
 * @param {String} exclude
 * @param {String} applyTo
 * @returns {Array}
 */
export function getElementsWithOption(rootEl, selector, exclude = false, applyTo = false) {
    let matchingEls = [...rootEl.querySelectorAll(selector)];
    if (rootEl.matches(selector)) {
        matchingEls.unshift(rootEl);
    }
    if (exclude) {
        matchingEls = matchingEls.filter((editingEl) => !editingEl.matches(exclude));
    }
    if (applyTo) {
        matchingEls = matchingEls.flatMap((editingEl) => [...editingEl.querySelectorAll(applyTo)]);
    }
    return matchingEls;
}

export function useOptionsSubEnv(getEditingElements) {
    useSubEnv({
        dependencyManager: new DependencyManager(),
        getEditingElement: () => getEditingElements()[0],
        getEditingElements: getEditingElements,
        weContext: {},
    });
}

export function getValueFromVar(value) {
    const match = value.match(/var\(--([a-zA-Z0-9-_]+)\)/);
    if (match) {
        return match[1];
    }
    return value;
}

/**
 * Converts a value to a ratio.
 *
 * @param {string} value
 */
export function toRatio(value) {
    const inputValueAsNumber = Number(value);
    const ratio = inputValueAsNumber >= 0 ? 1 + inputValueAsNumber : 1 / (1 - inputValueAsNumber);
    return `${ratio.toFixed(2)}x`;
}

/**
 * Filters an array of classes to only include those that extend a given class.
 */
export function filterExtends(arr, PotentialSuperClass) {
    return arr.filter((PotentialSubClass) =>
        doesExtendsClass(PotentialSubClass, PotentialSuperClass)
    );
}

/**
 * Checks if a `potentialSubClass` directly or indirectly extends a
 * `potentialSuperClass`.
 *
 * The implementation leverages the fact that classes are functions and their
 * prototype chain reflects the inheritance.
 *
 * @param {Function} PotentialSubClass The class that might be a subclass.
 * @param {Function} PotentialSuperClass The class that might be a superclass.
 * @returns {boolean} True if `potentialSubClass` extends `potentialSuperClass`,
 * false otherwise.
 */
export function doesExtendsClass(PotentialSubClass, PotentialSuperClass) {
    if (PotentialSubClass === PotentialSuperClass) {
        return false;
    }
    return PotentialSubClass.prototype instanceof PotentialSuperClass;
}

/**
 * Checks if the given element is editable.
 *
 * @param {HTMLElement} node the element
 * @returns {Boolean}
 */
export function isEditable(node) {
    let currentNode = node;
    while (currentNode) {
        if (currentNode.className && typeof currentNode.className === "string") {
            if (currentNode.className.includes("o_not_editable")) {
                return false;
            }
            if (currentNode.className.includes("o_editable")) {
                return true;
            }
        }
        currentNode = currentNode.parentNode;
    }
    return false;
}

/**
 * Removes the specified plugins from a given list of plugins.
 *
 * @param {Array<Plugin>} plugins the list of plugins
 * @param {Array<string>} pluginsToRemove the names of the plugins to remove
 * @returns {Array<Plugin>}
 */
export function removePlugins(plugins, pluginsToRemove) {
    return plugins.filter((p) => !pluginsToRemove.includes(p.name));
}

/**
 * Check if the given value is an integer smaller than 15 digits.
 * @param {String} value
 * @returns {Boolean}
 */
export function isSmallInteger(value) {
    return /^-?[0-9]{1,15}$/.test(value);
}
