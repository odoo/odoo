import { Cache } from "@web/core/utils/cache";

export class SyncCache {
    constructor(fn) {
        this.asyncCache = new Cache(fn, JSON.stringify);
        this.syncCache = new Map();
    }
    async preload(params) {
        const result = await this.asyncCache.read(params);
        this.syncCache.set(JSON.stringify(params), result);
        return result;
    }
    get(params) {
        return this.syncCache.get(JSON.stringify(params));
    }
    invalidate() {
        this.asyncCache.invalidate();
        this.syncCache.clear();
    }
}
