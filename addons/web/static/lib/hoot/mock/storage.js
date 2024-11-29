/** @odoo-module */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const { StorageEvent, String } = globalThis;

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export class MockStorage {
    get length() {
        return Object.keys(this).length;
    }

    /** @type {typeof Storage.prototype.clear} */
    clear() {
        for (const key in this) {
            delete this[key];
        }
    }

    /** @type {typeof Storage.prototype.getItem} */
    getItem(key) {
        key = String(key);
        return this[key] ?? null;
    }

    /** @type {typeof Storage.prototype.key} */
    key(index) {
        return Object.keys(this).at(index);
    }

    /** @type {typeof Storage.prototype.removeItem} */
    removeItem(key) {
        key = String(key);
        delete this[key];
        window.dispatchEvent(new StorageEvent("storage", { key, newValue: null }));
    }

    /** @type {typeof Storage.prototype.setItem} */
    setItem(key, value) {
        key = String(key);
        value = String(value);
        this[key] = value;
        window.dispatchEvent(new StorageEvent("storage", { key, newValue: value }));
    }
}
