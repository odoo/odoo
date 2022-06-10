/** @odoo-module **/

import { browser } from '@web/core/browser/browser';
import { MEDIAS_BREAKPOINTS, SIZES, uiService } from '@web/core/ui/ui_service';
import { patchWithCleanup } from "@web/../tests/helpers/utils";

import config from 'web.config';

/**
 * Return the width corresponding to the given size. If an upper and lower bound
 * are defined, returns the lower bound: this is an arbitrary choice that should
 * not impact anything. A test should pass the `width` parameter instead of `size`
 * if it needs a specific width to be set.
 *
 * @param {number} size
 * @returns {number} The width corresponding to the given size.
 */
function getWidthFromSize(size) {
    const { minWidth, maxWidth } = MEDIAS_BREAKPOINTS[size];
    return minWidth ? minWidth : maxWidth;
}

/**
 * Return the size corresponding to the given width.
 *
 * @param {number} width
 * @returns {number} The size corresponding to the given width.
 */
function getSizeFromWidth(width) {
    return MEDIAS_BREAKPOINTS.findIndex(({ minWidth, maxWidth }) => {
        if (!maxWidth) {
            return width >= minWidth;
        }
        if (!minWidth) {
            return width <= maxWidth;
        }
        return width >= minWidth && width <= maxWidth;
    });
}

/**
 * Patch legacy objects referring to the ui size. This function must be removed
 * when the wowl env will be available in the form_renderer (currently the form
 * renderer relies on config). This will impact env.browser.innerWidth,
 * env.device.isMobile and config.device.{size_class/isMobile}.
 *
 * @param {number} size
 * @param {number} width
 */
function legacyPatchUiSize(height, size, width) {
    const legacyEnv = owl.Component.env;
    patchWithCleanup(legacyEnv, {
        browser: {
            ...legacyEnv.browser,
            innerWidth: width,
            innerHeight: height || browser.innerHeight,
        },
        device: {
            ...legacyEnv.device,
            isMobile: size <= SIZES.SM,
        }
    });
    patchWithCleanup(config, {
        device: {
            ...config.device,
            size_class: size,
            isMobile: size <= SIZES.SM,
        },
    });
}

/**
 * Adjust ui size either from given size (mapped to window breakpoints) or
 * width. This will impact not only config.device.{size_class/isMobile} but
 * uiService.{isSmall/size}, (wowl/legacy) browser.innerWidth, (wowl)
 * env.isSmall and (legacy) env.device.isMobile. When a size is given, the browser
 * width is set according to the breakpoints that are used by the webClient.
 *
 * @param {Object} params parameters to configure the ui size.
 * @param {number|undefined} [params.size]
 * @param {number|undefined} [params.width]
 * @param {number|undefined} [params.height]
 */
function patchUiSize({ height, size, width }) {
    if (!size && !width || size && width) {
        throw new Error('Either size or width must be given to the patchUiSize function');
    }
    size = size === undefined ? getSizeFromWidth(width) : size;
    width = width || getWidthFromSize(size);

    patchWithCleanup(browser, {
        innerWidth: width,
        innerHeight: height || browser.innerHeight,
    });
    patchWithCleanup(uiService, {
        getSize() {
            return size;
        },
    });
    legacyPatchUiSize(height, size, width);
}

export {
    patchUiSize,
    SIZES
};
