/** @odoo-module */

import { registry } from "../registry";
import { browser } from "../browser/browser";
import { routeToUrl } from "../browser/router_service";
import { getCurrentDebugContext } from "./debug_context";

const commandProviderRegistry = registry.category("command_provider");

commandProviderRegistry.add("debug", {
    provide: (env) => {
        const result = [];
        if (env.services.user.isAdmin) {
            if (env.debug) {
                result.push({
                    action() {
                        const route = env.services.router.current;
                        route.search.debug = "";
                        browser.location.href = browser.location.origin + routeToUrl(route);
                    },
                    category: "debug",
                    name: "Deactivate debug mode",
                });
                result.push({
                    action() {
                        return {
                            placeHolder: "Choose a debug action...",
                            provide: async (env) => {
                                const debugContext = getCurrentDebugContext();
                                const items = await debugContext.getItems(env);
                                return items
                                    .filter((item) => item.type === "item")
                                    .map((item) => ({
                                        action: item.callback,
                                        name: item.description,
                                    }));
                            },
                        };
                    },
                    category: "debug",
                    name: "Debug menu",
                });
            } else {
                result.push({
                    action() {
                        browser.location.search = "?debug=assets";
                    },
                    category: "debug",
                    name: "Activate debug mode",
                });
            }
        }
        return result;
    },
});
