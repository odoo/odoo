import { usePlugin } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { router } from "@web/core/browser/router";
import { DebugModePlugin } from "@web/core/debug_mode_plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

const commandProviderRegistry = registry.category("command_provider");

commandProviderRegistry.add("debug", {
    provide(options) {
        const debugMode = usePlugin(DebugModePlugin);
        const result = [];
        if (debugMode.isActive()) {
            if (!debugMode.isActive("assets")) {
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
                    router.pushState({ debug: 0 }, { reload: true });
                },
                category: "debug",
                name: _t("Deactivate debug mode"),
            });
            result.push({
                action() {
                    browser.open("/web/tests?debug=assets");
                },
                category: "debug",
                name: _t("Run Unit Tests"),
            });
        } else {
            const debugKey = "debug";
            if (options.searchValue.toLowerCase() === debugKey) {
                result.push({
                    action() {
                        router.pushState({ debug: "1" }, { reload: true });
                    },
                    category: "debug",
                    name: `${_t("Activate debug mode")} (${debugKey})`,
                });
                result.push({
                    action() {
                        router.pushState({ debug: "assets" }, { reload: true });
                    },
                    category: "debug",
                    name: `${_t("Activate debug mode (with assets)")} (${debugKey})`,
                });
            }
        }
        return result;
    },
});
