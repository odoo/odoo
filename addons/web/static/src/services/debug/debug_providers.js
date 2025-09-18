// @ts-check

/**
 * Command palette provider that offers debug mode toggle commands.
 * Commands are contextual: when debug is active, shows "deactivate" and "run tests";
 * when inactive, shows "activate" only if the user types "debug" in the palette.
 *
 * @module @web/services/debug/debug_providers
 */

import { browser } from "@web/core/browser/browser";
import { router } from "@web/core/browser/router";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
const commandProviderRegistry = registry.category("command_provider");

commandProviderRegistry.add(
    "debug",
    /** @type {any} */ ({
        /**
         * @param {import("@web/env").OdooEnv} env
         * @param {{ searchValue: string }} options
         * @returns {import("@web/services/commands/command_service").Command[]}
         */
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
    }),
);
