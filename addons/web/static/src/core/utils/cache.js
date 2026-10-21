/**
 * @template [K=string]
 * @template [V=any]
 * @template [Args=any[]]
 */
export class Cache {
    /** @type {Record<string, V>} */
    cache = {};

    /**
     * @param {(...args: Args) => V} getValue
     * @param {(...args: Args) => K} [getKey]
     */
    constructor(getValue, getKey) {
        this.getKey = getKey;
        this.getValue = getValue;
    }
    /**
     * @param {Args} path
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
            key = path[path.length - 1];
        }
        return { cache, key };
    }
    /**
     * @param {Args} path
     */
    clear(...path) {
        const { cache, key } = this._getCacheAndKey(...path);
        delete cache[key];
    }
    invalidate() {
        this.cache = {};
    }
    /**
     * @param {Args} path
     * @returns {V}
     */
    read(...path) {
        const { cache, key } = this._getCacheAndKey(...path);
        if (!(key in cache)) {
            cache[key] = this.getValue(...path);
        }
        return cache[key];
    }
}
