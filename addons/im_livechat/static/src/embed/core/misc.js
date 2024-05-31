/**  @odoo-module */

import { browser } from "@web/core/browser/browser";

export function isValidEmail(val) {
    // http://stackoverflow.com/questions/46155/validate-email-address-in-javascript
    const re =
        /^(([^<>()[\].,;:\s@"]+(\.[^<>()[\].,;:\s@"]+)*)|(".+"))@(([^<>()[\].,;:\s@"]+\.)+[^<>()[\].,;:\s@"]{2,})$/i;
    return re.test(val);
}

export const expirableStorage = {
    getItem(key) {
        const item = browser.localStorage.getItem(key);
        if (item) {
            const { expires, value } = JSON.parse(item);
            if (expires && expires < Date.now()) {
                localStorage.removeItem(key);
                return null;
            }
            return value;
        }
        return null;
    },
    /**
     * @param {string} key
     * @param {string} value
     * @param {number} ttl Number of seconds after which the item should expire.
     */
    setItem(key, value, ttl) {
        let expires;
        if (ttl) {
            expires = Date.now() + ttl * 1000;
        }
        browser.localStorage.setItem(key, JSON.stringify({ value, expires }));
    },
    removeItem(key) {
        browser.localStorage.removeItem(key);
    },
};
