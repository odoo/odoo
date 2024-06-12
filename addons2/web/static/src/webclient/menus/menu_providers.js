/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { fuzzyLookup } from "@web/core/utils/search";
import { computeAppsAndMenuItems } from "@web/webclient/menus/menu_helpers";
import { DefaultCommandItem } from "@web/core/commands/command_palette";

import { Component } from "@odoo/owl";

class AppIconCommand extends Component {}
AppIconCommand.template = "web.AppIconCommand";
AppIconCommand.props = {
    webIconData: { type: String, optional: true },
    webIcon: { type: Object, optional: true },
    ...DefaultCommandItem.props,
};

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
commandProviderRegistry.add("menu", {
    namespace: "/",
    async provide(env, options) {
        const result = [];
        const menuService = env.services.menu;
        let { apps, menuItems } = computeAppsAndMenuItems(menuService.getMenuAsTree("root"));
        if (options.searchValue !== "") {
            apps = fuzzyLookup(options.searchValue, apps, (menu) => menu.label);

            fuzzyLookup(options.searchValue, menuItems, (menu) =>
                (menu.parents + " / " + menu.label).split("/").reverse().join("/")
            ).forEach((menu) => {
                result.push({
                    action() {
                        menuService.selectMenu(menu);
                    },
                    category: "menu_items",
                    name: menu.parents + " / " + menu.label,
                    href: menu.href || `#menu_id=${menu.id}&amp;action_id=${menu.actionID}`,
                });
            });
        }

        apps.forEach((menu) => {
            const props = {};
            if (menu.webIconData) {
                const prefix = menu.webIconData.startsWith("P")
                    ? "data:image/svg+xml;base64,"
                    : "data:image/png;base64,";
                props.webIconData = menu.webIconData.startsWith("data:image")
                    ? menu.webIconData
                    : prefix + menu.webIconData.replace(/\s/g, "");
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
                href: menu.href || `#menu_id=${menu.id}&amp;action_id=${menu.actionID}`,
                props,
            });
        });

        return result;
    },
});
