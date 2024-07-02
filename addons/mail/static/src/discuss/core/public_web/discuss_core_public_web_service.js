import { reactive } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";

import { registry } from "@web/core/registry";

export class DiscussCorePublicWeb {
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    constructor(env, services) {
        this.env = env;
        this.store = services["mail.store"];
        try {
            this.sidebarCategoriesBroadcast = new browser.BroadcastChannel(
                "discuss_core_public_web.sidebar_categories"
            );
        } catch {
            // BroadcastChannel API is not supported (e.g. Safari < 15.4), so disabling it.
        }
    }

    /**
     * Send the state of a category to the other tabs.
     *
     * @param {import("models").DiscussAppCategory} category
     */
    broadcastCategoryState(category) {
        this.sidebarCategoriesBroadcast?.postMessage({ id: category.id, open: category.open });
    }
}

export const discussCorePublicWeb = {
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    start(env, services) {
        return reactive(new DiscussCorePublicWeb(env, services));
    },
};

registry.category("services").add("discuss.core.public.web", discussCorePublicWeb);
