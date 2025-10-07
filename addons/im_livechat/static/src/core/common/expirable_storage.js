import { EventBus } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";

const BASE_STORAGE_KEY = "EXPIRABLE_STORAGE_";
const CLEAR_INTERVAL = 24 * 60 * 60 * 1000; // 24 hours in milliseconds

function cleanupExpirableStorage() {
    const now = Date.now();
    // Next line is for testing compatibility as for..in is not supported by
    // the `MockStorage` class.
    const keys = browser.localStorage.items?.keys() ?? Object.keys(browser.localStorage);
    for (const key of keys) {
        if (key.startsWith(BASE_STORAGE_KEY)) {
            const item = JSON.parse(browser.localStorage.getItem(key));
            if (item.expires && item.expires < now) {
                browser.localStorage.removeItem(key);
            }
        }
    }
}

const storageBus = new EventBus();
const storageFnToWrapper = new Map();
browser.addEventListener("storage", ({ key, newValue }) => {
    if (key?.startsWith(BASE_STORAGE_KEY)) {
        const actualKey = key.slice(BASE_STORAGE_KEY.length);
        storageBus.trigger(actualKey, newValue ? JSON.parse(newValue).value : null);
    }
});

export const expirableStorage = {
    /** @param {string} key */
    getItem(key) {
        cleanupExpirableStorage();
        const item = browser.localStorage.getItem(`${BASE_STORAGE_KEY}${key}`);
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
            `${BASE_STORAGE_KEY}${key}`,
            JSON.stringify({ value, expires })
        );
    },
    /** @param {string} key */
    removeItem(key) {
        browser.localStorage.removeItem(`${BASE_STORAGE_KEY}${key}`);
    },
    /**
     * @param {string} key
     * @param {(value: any) => void} fn
     */
    onChange(key, fn) {
        storageFnToWrapper.set(fn, ({ detail }) => fn(detail));
        storageBus.addEventListener(key, storageFnToWrapper.get(fn));
    },
    /**
     * @param {string} key
     * @param {(value: any) => void} fn
     */
    offChange(key, fn) {
        storageBus.removeEventListener(key, storageFnToWrapper.get(fn));
        storageFnToWrapper.delete(fn);
    },
};

cleanupExpirableStorage();
setInterval(cleanupExpirableStorage, CLEAR_INTERVAL);
