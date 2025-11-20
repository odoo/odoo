import { browser } from "@web/core/browser/browser";
import { session } from "@web/session";

const LOCAL_STORAGE_SUBVERSION = 0;

/**
 * @typedef {Object} VersionedLocalStorageValue
 * @property {any} value
 * @property {string} version
 */

export function getCurrentLocalStorageVersion() {
    try {
        const [major, minor] = session.server_version_info;
        return [major, minor, LOCAL_STORAGE_SUBVERSION].join(".");
    } catch (err) {
        console.warn(
            "Could not parse server_version_info from session (probably missing). Please provide it!"
        );
        throw err;
    }
}

/**
 * Utility class to simplify interaction on local storage with constant local storage key.
 * When a value is set, this is done as `{ value, version }`.
 * Note: The object syntax is necessary to properly handle types, like "false" vs false.
 */
export class LocalStorageEntry {
    /** @type {string} */
    key;
    constructor(key) {
        this.key = key;
    }
    get() {
        const rawValue = this.rawGet();
        if (rawValue === null) {
            return undefined;
        }
        return parseRawValue(rawValue)?.value;
    }
    getVersioned() {
        const rawValue = this.rawGet();
        if (rawValue === null) {
            return undefined;
        }
        const versionedValue = parseRawValue(rawValue);
        if (!versionedValue || typeof versionedValue !== "object") {
            return undefined;
        }
        return versionedValue;
    }
    set(value, version = getCurrentLocalStorageVersion()) {
        if (this.rawGet() !== null && this.get() === value) {
            return;
        }
        browser.localStorage.setItem(this.key, toRawValue(value, version));
    }
    rawGet() {
        return browser.localStorage.getItem(this.key);
    }
    remove() {
        if (this.rawGet() === null) {
            return;
        }
        browser.localStorage.removeItem(this.key);
    }
}

export function toRawValue(value, version = getCurrentLocalStorageVersion()) {
    return JSON.stringify({ value, version });
}

/**
 * @param {string} rawValue
 * @returns {VersionedLocalStorageValue}
 */
export function parseRawValue(rawValue) {
    try {
        return JSON.parse(rawValue);
    } catch {
        return undefined;
    }
}
