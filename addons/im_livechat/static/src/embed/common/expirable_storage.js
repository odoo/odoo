/* @odoo-module */

import { browser } from "@web/core/browser/browser";

const BASE_STORAGE_KEY = "EXPIRABLE_STORAGE";
const CLEAR_INTERVAL = 24 * 60 * 60 * 1000; // 24 hours in milliseconds

function cleanupExpirableStorage() {
    const now = Date.now();
    for (const key of Object.keys(browser.localStorage)) {
        if (key.startsWith(BASE_STORAGE_KEY)) {
            const item = JSON.parse(browser.localStorage.getItem(key));
            if (item.expires && item.expires < now) {
                browser.localStorage.removeItem(key);
            }
        }
    }
}

export const expirableStorage = {
    /** @param {string} key */
    getItem(key) {
        cleanupExpirableStorage();
        const item = browser.localStorage.getItem(`${BASE_STORAGE_KEY}_${key}`);
        if (item) {
            return JSON.parse(item).value;
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
        browser.localStorage.setItem(
            `${BASE_STORAGE_KEY}_${key}`,
            JSON.stringify({ value, expires })
        );
    },
    /** @param {string} key */
    removeItem(key) {
        browser.localStorage.removeItem(`${BASE_STORAGE_KEY}_${key}`);
    },
};

cleanupExpirableStorage();
setInterval(cleanupExpirableStorage, CLEAR_INTERVAL);
