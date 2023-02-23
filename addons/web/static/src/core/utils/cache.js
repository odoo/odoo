/** @odoo-module **/

export class Cache {
    constructor(getValue, getKey) {
        this.cache = {};
        this.getKey = getKey;
        this.getValue = getValue;
    }
    read(...path) {
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
        if (!(key in cache)) {
            cache[key] = this.getValue(...path);
        }
        return cache[key];
    }
}
