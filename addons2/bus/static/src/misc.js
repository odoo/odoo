/** @odoo-module */

import { browser } from "@web/core/browser/browser";

/**
 * Returns a function, that, when invoked, will only be triggered at most once
 * during a given window of time. Normally, the throttled function will run
 * as much as it can, without ever going more than once per `wait` duration;
 * but if you'd like to disable the execution on the leading edge, pass
 * `{leading: false}`. To disable execution on the trailing edge, ditto.
 *
 * credit to `underscore.js`
 */
function throttle(func, wait, options) {
    let timeout, context, args, result;
    let previous = 0;
    if (!options) {
        options = {};
    }

    const later = function () {
        previous = options.leading === false ? 0 : Date.now();
        timeout = null;
        result = func.apply(context, args);
        if (!timeout) {
            context = args = null;
        }
    };

    const throttled = function () {
        const _now = Date.now();
        if (!previous && options.leading === false) {
            previous = _now;
        }
        const remaining = wait - (_now - previous);
        context = this;
        args = arguments;
        if (remaining <= 0 || remaining > wait) {
            if (timeout) {
                browser.clearTimeout(timeout);
                timeout = null;
            }
            previous = _now;
            result = func.apply(context, args);
            if (!timeout) {
                context = args = null;
            }
        } else if (!timeout && options.trailing !== false) {
            timeout = browser.setTimeout(later, remaining);
        }
        return result;
    };

    throttled.cancel = function () {
        browser.clearTimeout(timeout);
        previous = 0;
        timeout = context = args = null;
    };

    return throttled;
}

export const timings = {
    throttle,
};
