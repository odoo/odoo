import { registry } from "@web/core/registry";

export const websiteMenusService = {
    start() {
        const updateCallbacks = new Set();
        return {
            updateCallbacks,
            registerCallback(fn) {
                updateCallbacks.add(fn);
                return () => updateCallbacks.delete(fn);
            },
            triggerCallbacks() {
                for (const callback of updateCallbacks) {
                    callback();
                }
            },
        };
    },
};

registry.category("services").add("website_menus", websiteMenusService);
