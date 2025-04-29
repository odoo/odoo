import { DependencyManager } from "../core/dependency_manager";
import { useSubEnv } from "@odoo/owl";
import { SIZES, MEDIAS_BREAKPOINTS } from "@web/core/ui/ui_service";
import { _t } from "@web/core/l10n/translation";
import { isVisible } from "@web/core/utils/ui";

/**
 * Checks if the view of the targeted element is mobile.
 *
 * @param {HTMLElement} targetEl - target of the editor
 * @returns {boolean}
 */
export function isMobileView(targetEl) {
    const mobileViewThreshold = MEDIAS_BREAKPOINTS[SIZES.LG].minWidth;
    const clientWidth =
        targetEl.ownerDocument.defaultView?.frameElement?.clientWidth ||
        targetEl.ownerDocument.documentElement.clientWidth;
    return clientWidth && clientWidth < mobileViewThreshold;
}

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
 * Checks if the element is visible while editing. Checks the current state of
 * the element itself (@see isVisible for the limits) and that it doesn't have a
 * `data-invisible` ancestor.
 *
 * @param {HTMLElement} el
 * @returns {Boolean}
 */
export function isElementVisible(el) {
    return isVisible(el) && !el.closest("[data-invisible='1']");
}

/**
 * Gets all the elements matching an option selector/exclude starting from the
 * root element.
 *
 * @param {HTMLElement} rootEl
 * @param {String} selector
 * @param {String} exclude
 * @returns {Array}
 */
export function getElementsWithOption(rootEl, selector, exclude = false) {
    let matchingEls = [...rootEl.querySelectorAll(selector)];
    if (rootEl.matches(selector)) {
        matchingEls.unshift(rootEl);
    }
    if (exclude) {
        matchingEls = matchingEls.filter((editingEl) => !editingEl.matches(exclude));
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
 * Returns the list of selector, exclude and applyTo on which an option is
 * applied.
 * @param {Array<Object>} builderOptions - All the builder options
 * @param {Class} optionClass - The applied option
 */
export function getSelectorParams(builderOptions, optionClass) {
    const selectorParams = [];
    const optionClassName = optionClass.name;
    for (const builderOption of builderOptions) {
        const { OptionComponent } = builderOption;
        if (
            OptionComponent &&
            (OptionComponent.name === optionClassName ||
                OptionComponent.prototype instanceof optionClass)
        ) {
            selectorParams.push(builderOption);
        }
    }
    return selectorParams;
}
