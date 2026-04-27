/** @odoo-module **/

import { browser } from "@web/core/browser/browser";

import { onMounted, onWillUnmount } from "@odoo/owl";

/**
 * Creates an interval that will call the given callback every
 * `duration` ms.
 * @param {Function} callback
 * @param {Number} duration
 */
export function useInterval(callback, duration) {
    let interval;
    onMounted(() => (interval = browser.setInterval(callback, duration)));
    onWillUnmount(() => browser.clearInterval(interval));
}
