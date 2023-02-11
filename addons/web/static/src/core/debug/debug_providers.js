/** @odoo-module */

import { registry } from "../registry";
import { browser } from "../browser/browser";
import { routeToUrl } from "../browser/router_service";

const commandProviderRegistry = registry.category("command_provider");

commandProviderRegistry.add("debug", {
    provide: (env, options) => {
        const result = [];
        if (env.debug) {
            result.push({
                action() {
                    const route = env.services.router.current;
                    route.search.debug = "";
                    browser.location.href = browser.location.origin + routeToUrl(route);
                },
                category: "debug",
                name: env._t("Deactivate debug mode"),
            });
        } else {
            if (options.searchValue.toLowerCase() === "debug") {
                result.push({
                    action() {
                        browser.location.search = "?debug=assets";
                    },
                    category: "debug",
                    name: env._t("Activate debug mode"),
                });
            }
        }
        return result;
    },
});
