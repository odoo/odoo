export class Cache {
    constructor(getValue, getKey) {
        this.cache = {};
        this.getKey = getKey;
        this.getValue = getValue;
    }
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
    clear(...path) {
        const { cache, key } = this._getCacheAndKey(...path);
        delete cache[key];
    }
    invalidate() {
        this.cache = {};
    }
    read(...path) {
        const { cache, key } = this._getCacheAndKey(...path);
        if (!(key in cache)) {
            cache[key] = this.getValue(...path);
        }
        return cache[key];
    }
}
