import { SIZES, MEDIAS_BREAKPOINTS } from "@web/core/ui/ui_service";

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
