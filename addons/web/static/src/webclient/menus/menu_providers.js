// @ts-check

/** @module @web/webclient/menus/menu_providers - Command palette providers for app and menu item fuzzy search */

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { fuzzyLookup } from "@web/core/utils/search";
import { DefaultCommandItem } from "@web/services/commands/command_palette";
import { computeAppsAndMenuItems } from "@web/webclient/menus/menu_helpers";

/** Command palette item renderer that shows the app icon next to the label. */
class AppIconCommand extends Component {
    static template = "web.AppIconCommand";
    static props = {
        webIconData: { type: String, optional: true },
        webIcon: { type: Object, optional: true },
        ...DefaultCommandItem.props,
    };
}

const commandCategoryRegistry = registry.category("command_categories");
commandCategoryRegistry.add("apps", { namespace: "/" }, { sequence: 10 });
commandCategoryRegistry.add("menu_items", { namespace: "/" }, { sequence: 20 });

const commandSetupRegistry = registry.category("command_setup");
commandSetupRegistry.add("/", {
    emptyMessage: _t("No menu found"),
    name: _t("menus"),
    placeholder: _t("Search for a menu..."),
});

const commandProviderRegistry = registry.category("command_provider");
commandProviderRegistry.add(
    "menu",
    /** @type {any} */ ({
        namespace: "/",
        async provide(env, options) {
            const result = [];
            const menuService = env.services.menu;
            const computed = computeAppsAndMenuItems(menuService.getMenuAsTree("root"));
            const { menuItems } = computed;
            let { apps } = computed;
            if (options.searchValue !== "") {
                apps = fuzzyLookup(options.searchValue, apps, (menu) => menu.label);

                fuzzyLookup(options.searchValue, menuItems, (menu) =>
                    `${menu.parents} / ${menu.label}`.split("/").reverse().join("/"),
                ).forEach((menu) => {
                    result.push({
                        action() {
                            menuService.selectMenu(menu);
                        },
                        category: "menu_items",
                        name: `${menu.parents} / ${menu.label}`,
                        href:
                            menu.href ||
                            `#menu_id=${menu.id}&action_id=${menu.actionID}`,
                    });
                });
            }

            apps.forEach((menu) => {
                // webIconData is already a valid src value from the server:
                // either a data URI (data:image/...;base64,...) or a URL path.
                const props = {};
                if (menu.webIconData) {
                    props.webIconData = menu.webIconData;
                } else {
                    props.webIcon = menu.webIcon;
                }
                result.push({
                    Component: AppIconCommand,
                    action() {
                        menuService.selectMenu(menu);
                    },
                    category: "apps",
                    name: menu.label,
                    href: menu.href || `#menu_id=${menu.id}&action_id=${menu.actionID}`,
                    props,
                });
            });

            return result;
        },
    }),
);
