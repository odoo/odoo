// @ts-check
/** @odoo-module native */

/** @template [T=any] */
export class LruCache {
    /**
     * @param {number} limit
     * @param {{ onEvict?: (key: string, value: T) => void }} [options]
     */
    constructor(limit, { onEvict } = {}) {
        this.limit = limit;
        /** @type {((key: string, value: T) => void) | null} */
        this._onEvict = onEvict ?? null;
        /** @type {Map<string, T>} */
        this._entries = new Map();
    }

    get limit() {
        return this._limit;
    }

    /** @param {number} limit */
    set limit(limit) {
        if (!Number.isInteger(limit) || limit < 0) {
            throw new RangeError("LruCache capacity must be a nonnegative integer");
        }
        this._limit = limit;
    }

    /** @returns {number} */
    get size() {
        return this._entries.size;
    }

    /**
     * @param {string} key
     * @returns {boolean}
     */
    has(key) {
        return this._entries.has(key);
    }

    /**
     * @param {string} key
     * @returns {T | undefined}
     */
    get(key) {
        if (!this._entries.has(key)) {
            return undefined;
        }
        const value = /** @type {T} */ (this._entries.get(key));
        this._entries.delete(key);
        this._entries.set(key, value);
        return value;
    }

    /**
     * @param {string} key
     * @param {T} value
     * @returns {this}
     */
    set(key, value) {
        this._entries.delete(key);
        this._entries.set(key, value);
        while (this._entries.size > this.limit) {
            const coldest = /** @type {string} */ (this._entries.keys().next().value);
            const evicted = /** @type {T} */ (this._entries.get(coldest));
            this._entries.delete(coldest);
            this._onEvict?.(coldest, evicted);
        }
        return this;
    }

    /**
     * @param {string} key
     * @returns {T | undefined}
     */
    peek(key) {
        return this._entries.get(key);
    }

    /**
     * @param {string} key
     * @returns {void}
     */
    touch(key) {
        this.get(key);
    }

    /**
     * @param {string} key
     * @returns {boolean}
     */
    delete(key) {
        return this._entries.delete(key);
    }

    /** @returns {void} */
    clear() {
        this._entries.clear();
    }
}
