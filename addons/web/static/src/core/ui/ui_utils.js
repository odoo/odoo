import { getTabableElements } from "@web/core/utils/ui";

export const SIZES = { XS: 0, SM: 1, MD: 2, LG: 3, XL: 4, XXL: 5 };

export function getFirstAndLastTabableElements(el) {
    const tabableEls = getTabableElements(el);
    return [tabableEls[0], tabableEls[tabableEls.length - 1]];
}

// window size handling
export const MEDIAS_BREAKPOINTS = [
    { maxWidth: 575 },
    { minWidth: 576, maxWidth: 767 },
    { minWidth: 768, maxWidth: 991 },
    { minWidth: 992, maxWidth: 1199 },
    { minWidth: 1200, maxWidth: 1399 },
    { minWidth: 1400 },
];

/**
 * Create the MediaQueryList used both by the uiService and config from
 * `MEDIA_BREAKPOINTS`.
 *
 * @returns {MediaQueryList[]}
 */
export function getMediaQueryLists() {
    return MEDIAS_BREAKPOINTS.map(({ minWidth, maxWidth }) => {
        if (!maxWidth) {
            return window.matchMedia(`(min-width: ${minWidth}px)`);
        }
        if (!minWidth) {
            return window.matchMedia(`(max-width: ${maxWidth}px)`);
        }
        return window.matchMedia(`(min-width: ${minWidth}px) and (max-width: ${maxWidth}px)`);
    });
}

// window size handling.
let MEDIAS = [];

export const utils = {
    getSize() {
        return MEDIAS.findIndex((media) => media.matches);
    },
    /**
     * @param ui UIPlugin
     */
    isSmall(ui) {
        return (ui?.size() || utils.getSize()) <= SIZES.SM;
    },
};

/**
 * Recomputes the `MediaQueryList` used by `utils.getSize()`/`utils.isSmall()`.
 * Called by `UIPlugin` on setup so that a freshly (re)started plugin (e.g. in
 * tests, where a new app/plugin is created for each test) picks up the
 * current `window.matchMedia` implementation.
 *
 * @returns {MediaQueryList[]} the freshly computed list, for the caller to
 *  attach its own "change" listeners on.
 */
export function refreshMedias() {
    MEDIAS = getMediaQueryLists();
    return MEDIAS;
}
