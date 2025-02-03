import { SIZES, MEDIAS_BREAKPOINTS } from "@web/core/ui/ui_service";
import { _t } from "@web/core/l10n/translation";

const oeStructureSelector = "#wrapwrap .oe_structure[data-oe-xpath][data-oe-id]";
const oeFieldSelector = "#wrapwrap [data-oe-field]:not([data-oe-sanitize-prevent-edition])";
const OE_RECORD_COVER_SELECTOR = "#wrapwrap .o_record_cover_container[data-res-model]";
const oeCoverSelector = `#wrapwrap .s_cover[data-res-model], ${OE_RECORD_COVER_SELECTOR}`;
export const SAVABLE_SELECTOR = `${oeStructureSelector}, ${oeFieldSelector}, ${oeCoverSelector}`;

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
