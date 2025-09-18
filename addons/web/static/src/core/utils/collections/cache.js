// @ts-check

/** @module @web/core/utils/collections/cache - Generic key-path cache with lazy value computation */

/**
 * A generic cache that stores values indexed by a key derived from the lookup
 * path. When a value is not found, it is computed via the `getValue` callback
 * and stored for future reads.
 *
 * @template T
 */
export class Cache {
    /**
     * @param {(...args: any[]) => T} getValue called to compute a missing value
     * @param {((...args: any[]) => string) | undefined} [getKey] derives a flat
     *   cache key from the path arguments. When omitted, the path is used to
     *   build a nested object structure with the last segment as key.
     */
    constructor(getValue, getKey) {
        /** @type {Record<string, any>} */
        this.cache = {};
        this.getKey = getKey;
        this.getValue = getValue;
    }

    /**
     * @param {any[]} path
     * @returns {{ cache: Record<string, any>, key: string }}
     */
    _getCacheAndKey(...path) {
        let cache = this.cache;
        let key;
        if (this.getKey) {
            key = this.getKey(...path);
        } else {
            for (let i = 0; i < path.length - 1; i++) {
                cache = cache[path[i]] = cache[path[i]] || {};
            }
            key = path.at(-1);
        }
        return { cache, key };
    }

    /**
     * Remove a single cached entry identified by `path`.
     *
     * @param {any[]} path
     */
    clear(...path) {
        const { cache, key } = this._getCacheAndKey(...path);
        delete cache[key];
    }

    /** Flush the entire cache. */
    invalidate() {
        this.cache = {};
    }

    /**
     * Return the cached value for `path`, computing it via `getValue` if absent.
     *
     * @param {any[]} path
     * @returns {T}
     */
    read(...path) {
        const { cache, key } = this._getCacheAndKey(...path);
        if (!(key in cache)) {
            cache[key] = this.getValue(...path);
        }
        return cache[key];
    }
}
