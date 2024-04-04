/** @odoo-module */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const { Map, StorageEvent, String } = globalThis;

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export class MockStorage {
    constructor() {
        this.items = new Map();
    }

    get length() {
        return this.items.size;
    }

    /** @type {typeof Storage.prototype.clear} */
    clear() {
        this.items.clear();
    }

    /** @type {typeof Storage.prototype.getItem} */
    getItem(key) {
        return this.items.get(key) ?? null;
    }

    /** @type {typeof Storage.prototype.key} */
    key(index) {
        return [...this.items.keys()].at(index);
    }

    /** @type {typeof Storage.prototype.removeItem} */
    removeItem(key) {
        this.items.delete(key);
        window.dispatchEvent(new StorageEvent("storage", { key, newValue: null }));
    }

    /** @type {typeof Storage.prototype.setItem} */
    setItem(key, value) {
        this.items.set(key, String(value));
        window.dispatchEvent(new StorageEvent("storage", { key, newValue: value }));
    }
}
