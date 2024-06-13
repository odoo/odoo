/** @odoo-module */

import { queryAll } from "@odoo/hoot-dom";

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * @param {string} url
 */
export function parseUrl(url) {
    return url.replace(/^.*hoot\/tests/, "@hoot").replace(/(\.test)?\.js$/, "");
}

export function waitForIframes() {
    return Promise.all(
        queryAll("iframe").map(
            (iframe) => new Promise((resolve) => iframe.addEventListener("load", resolve))
        )
    );
}
