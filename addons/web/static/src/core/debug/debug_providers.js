import { _t } from "@web/core/l10n/translation";
import { registry } from "../registry";
import { browser } from "../browser/browser";
import { router } from "../browser/router";

const commandProviderRegistry = registry.category("command_provider");

commandProviderRegistry.add("debug", {
    provide: (env, options) => {
        const result = [];
        if (env.debug) {
            if (!env.debug.includes("assets")) {
                result.push({
                    action() {
                        router.pushState({ debug: "assets" }, { reload: true });
                    },
                    category: "debug",
                    name: _t("Activate debug mode (with assets)"),
                });
            }
            result.push({
                action() {
                    router.pushState({ debug: undefined }, { reload: true });
                },
                category: "debug",
                name: _t("Deactivate debug mode"),
            });
            result.push({
                action() {
                    browser.open("/web/tests/next?debug=assets");
                },
                category: "debug",
                name: _t("Run unit tests"),
            });
            result.push({
                action() {
                    browser.open("/web/tests?debug=assets");
                },
                category: "debug",
                name: _t("Run QUnit tests (legacy)"),
            });
            result.push({
                action() {
                    browser.open("/web/tests/mobile?debug=assets");
                },
                category: "debug",
                name: _t("Run QUnit mobile tests (legacy)"),
            });
        } else {
            if (options.searchValue.toLowerCase() === "debug") {
                result.push({
                    action() {
                        router.pushState({ debug: "assets" }, { reload: true });
                    },
                    category: "debug",
                    name: _t("Activate debug mode (with assets)"),
                });
            }
        }
        return result;
    },
});
