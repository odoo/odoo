/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "../registry";
import { browser } from "../browser/browser";
import { routeToUrl, router } from "../browser/router";

const commandProviderRegistry = registry.category("command_provider");

commandProviderRegistry.add("debug", {
    provide: (env, options) => {
        const result = [];
        if (env.debug) {
            if (!env.debug.includes("assets")) {
                result.push({
                    action() {
                        browser.location.search = "?debug=assets";
                    },
                    category: "debug",
                    name: _t("Activate debug mode (with assets)"),
                });
            }
            result.push({
                action() {
                    const route = router.current;
                    route.search.debug = "";
                    browser.location.href = browser.location.origin + routeToUrl(route);
                },
                category: "debug",
                name: _t("Deactivate debug mode"),
            });
            result.push({
                action: () => browser.open("/web/tests/next?debug=assets"),
                category: "debug",
                name: _t("Run unit tests"),
            });
            result.push({
                action: () => browser.open("/web/tests?debug=assets"),
                category: "debug",
                name: _t("Run QUnit tests (legacy)"),
            });
            result.push({
                action: () => browser.open("/web/tests/mobile?debug=assets"),
                category: "debug",
                name: _t("Run QUnit mobile tests (legacy)"),
            });
        } else {
            if (options.searchValue.toLowerCase() === "debug") {
                result.push({
                    action() {
                        browser.location.search = "?debug=assets";
                    },
                    category: "debug",
                    name: _t("Activate debug mode (with assets)"),
                });
            }
        }
        return result;
    },
});
