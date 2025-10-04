/** @odoo-module **/

import { browser } from "@web/core/browser/browser";

const BOOLEAN = {
    toLocalStorage: (val) => (val ? "1" : "0"),
    fromLocalStorage: (val) => (val === "1" ? true : false),
};

const INTEGER = {
    toLocalStorage: (val) => val.toString(),
    fromLocalStorage: (val) => parseInt(val, 10),
};

const STRING = {
    toLocalStorage: (x) => x,
    fromLocalStorage: (x) => x,
};

const ALLOWED_KEYS = {
    // Don't close the 'watch' browser when the tour failed.
    keepWatchBrowser: BOOLEAN,

    // Duration at which the pointer is shown in auto mode.
    showPointerDuration: INTEGER,

    // Index of the current step.
    currentIndex: INTEGER,

    // Global step delay that is specified before starting the tour.
    stepDelay: INTEGER,

    // 'auto' | 'manual' - important that it's persisted because it's only specified during start of tour.
    mode: STRING,

    // Used to order the tours.
    sequence: INTEGER,
};

function getPrefixedName(tourName, key) {
    return `tour__${tourName}__${key}`;
}

function destructurePrefixedName(prefixedName) {
    const match = prefixedName.match(/tour__([.\w]+)__([\w]+)/);
    return match ? [match[1], match[2]] : null;
}

/**
 * Wrapper around localStorage for persistence of the running tours.
 * Useful for resuming running tours when the page refreshed.
 */
export const tourState = {
    get(tourName, key) {
        if (!(key in ALLOWED_KEYS)) {
            throw new Error(`Invalid key: '${key}' (tourName = '${tourName}')`);
        }
        const prefixedName = getPrefixedName(tourName, key);
        const savedValue = browser.localStorage.getItem(prefixedName);
        return ALLOWED_KEYS[key].fromLocalStorage(savedValue);
    },
    set(tourName, key, value) {
        if (!(key in ALLOWED_KEYS)) {
            throw new Error(`Invalid key: '${key}' (tourName = '${tourName}')`);
        }
        const prefixedName = getPrefixedName(tourName, key);
        browser.localStorage.setItem(prefixedName, ALLOWED_KEYS[key].toLocalStorage(value));
    },
    clear(tourName) {
        for (const key in ALLOWED_KEYS) {
            const prefixedName = getPrefixedName(tourName, key);
            browser.localStorage.removeItem(prefixedName);
        }
    },
    getActiveTourNames() {
        const tourNames = new Set();
        for (const key of Object.keys(browser.localStorage)) {
            const [tourName] = destructurePrefixedName(key) || [false];
            if (tourName) {
                tourNames.add(tourName);
            }
        }
        return [...tourNames].sort((a, b) => this.get(a, "sequence") - this.get(b, "sequence"));
    },
};
