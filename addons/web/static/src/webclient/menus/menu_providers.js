/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { computeAppsAndMenuItems } from "@web/webclient/menus/menu_helpers";
import { fuzzyLookup } from "@web/core/utils/search";

const { Component } = owl;

class AppIconCommand extends Component {}
AppIconCommand.template = "web.AppIconCommand";

const commandCategoryRegistry = registry.category("command_categories");
commandCategoryRegistry.add("apps", { namespace: "/" }, { sequence: 10 });
commandCategoryRegistry.add("menu_items", { namespace: "/" }, { sequence: 20 });

const commandEmptyMessageRegistry = registry.category("command_empty_list");
commandEmptyMessageRegistry.add("/", _lt("No menu found"));

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
                });
            });
        }

        apps.forEach((menu) => {
            const props = {};
            if (menu.webIconData) {
                const prefix = "data:image/png;base64,";
                props.webIconData = menu.webIconData.startsWith(prefix)
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
                props,
            });
        });

        return result;
    },
});
