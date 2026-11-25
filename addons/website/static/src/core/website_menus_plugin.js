import { Plugin, usePlugin } from "@odoo/owl";
import { services } from "@web/core/services";
import { registry } from "@web/core/registry";

export class WebsiteMenusPlugin extends Plugin {
    updateCallbacks = new Set();

    registerCallback(fn) {
        this.updateCallbacks.add(fn);
        return () => this.updateCallbacks.delete(fn);
    }

    triggerCallbacks() {
        for (const callback of this.updateCallbacks) {
            callback();
        }
    }
}

services.add(WebsiteMenusPlugin);

/**
 * ----------------------------------------------------------------------------
 * @todo owl3 migration
 * Temporary - to remove when all uses of the "website_menus" service are
 * removed
 * ----------------------------------------------------------------------------
 */
registry.category("services").add("website_menus", {
    start() {
        return usePlugin(WebsiteMenusPlugin);
    },
});
