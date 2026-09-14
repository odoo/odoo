// @ts-check
/** @odoo-module native */

import { Component } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { COG_GROUP } from "@web/search/cog_menu/cog_menu_group";
import { CogMenuItem } from "@web/search/cog_menu/cog_menu_item";
const cogMenuRegistry = registry.category("cogMenu");

const moduleUpdateCache = new WeakMap();

export class ResetModuleStateCogMenu extends Component {
    static template = "web.ResetModuleStateCogMenu";
    static components = { CogMenuItem };
    static props = {};

    /** @type {import("services").ServiceFactories["orm"]} */
    orm;

    setup() {
        this.orm = useService("orm");
    }

    async resetModuleState() {
        await this.orm.call("ir.module.module", "button_reset_state", [], {});
        browser.location.reload();
    }
}

cogMenuRegistry.add(
    "reset-module-state-cog-menu",
    /** @type {any} */ ({
        Component: ResetModuleStateCogMenu,
        groupNumber: COG_GROUP.APP,
        /** @param {{ config: any, searchModel: any, services: any }} param0 */
        isDisplayed: async ({ config, searchModel, services }) => {
            if (
                searchModel.resModel !== "ir.module.module" ||
                config.viewType === "form"
            ) {
                return false;
            }
            if (!moduleUpdateCache.has(config)) {
                moduleUpdateCache.set(
                    config,
                    (async () => {
                        try {
                            return Boolean(
                                await services.orm.silent.call(
                                    "ir.module.module",
                                    "has_pending_module_update",
                                    [],
                                    {},
                                ),
                            );
                        } catch {
                            return false;
                        }
                    })(),
                );
            }
            return moduleUpdateCache.get(config);
        },
    }),
);
