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
                    name: "Deactivate debug mode",
                    category: "debug",
                    action: () => {
                        const route = env.services.router.current;
                        route.search.debug = "";
                        browser.location.href = browser.location.origin + routeToUrl(route);
                    },
                });
                result.push({
                    name: "Debug menu",
                    category: "debug",
                    action: () => {
                        return {
                            placeHolder: "Choose a debug action...",
                            provide: async (env) => {
                                const debugContext = getCurrentDebugContext();
                                const items = await debugContext.getItems(env);
                                return items
                                    .filter((item) => item.type === "item")
                                    .map((item) => ({
                                        name: item.description,
                                        action: item.callback,
                                    }));
                            },
                        };
                    },
                });
            } else {
                result.push({
                    name: "Activate debug mode",
                    category: "debug",
                    action: () => {
                        browser.location.search = "?debug=assets";
                    },
                });
            }
        }
        return result;
    },
});
