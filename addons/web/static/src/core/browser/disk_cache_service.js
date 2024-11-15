import { registry } from "@web/core/registry";
import { DiskCache } from "./disk_cache";

export const diskCacheService = {
    start(env) {
        const cache = new DiskCache("odoo");
        env.bus.addEventListener("CLEAR-CACHES", () => cache.invalidate());
        return cache;
    },
};

registry.category("services").add("disk_cache", diskCacheService);
