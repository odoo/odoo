import { useEnv, useLayoutEffect } from "@web/owl2/utils";
import { registries } from "@odoo/o-spreadsheet";
import { registry } from "@web/core/registry";
import { DefaultCommandItem } from "@web/core/commands/command_palette";
import { HotkeyCommandItem } from "@web/core/commands/default_providers";

const { topbarMenuRegistry } = registries;
const commandProviderRegistry = registry.category("command_provider");
const commandCategoryRegistry = registry.category("command_categories");

/**
 * Activate the command palette for spreadsheet.
 */
export function useSpreadsheetCommandPalette() {
    const env = useEnv();
    useLayoutEffect(
        () => {
            setupSpreadsheetCategories(env);
            setupSpreadsheetCommandProvider(env);
            return () => commandProviderRegistry.remove("spreadsheet_provider");
        },
        () => []
    );
}

function setupSpreadsheetCategories(spreadsheetEnv) {
    let sequence = 5;
    commandCategoryRegistry.add("spreadsheet_insert_link", {}, { sequence: 0, force: true });
    for (const menu of topbarMenuRegistry.getMenuItems()) {
        const category = `spreadsheet_${menu.name(spreadsheetEnv)}`;
        commandCategoryRegistry.add(category, {}, { sequence, force: true });
        sequence++;
    }
}

function setupSpreadsheetCommandProvider(spreadsheetEnv) {
    commandProviderRegistry.add("spreadsheet_provider", {
        provide: (env, options) => {
            const result = [];
            for (const menu of topbarMenuRegistry.getMenuItems()) {
                const name = menu.name(spreadsheetEnv);
                const category = `spreadsheet_${name}`;
                result.push(...registerCommand(spreadsheetEnv, menu, name, category));
            }
            return result;
        },
    });
}

function registerCommand(spreadsheetEnv, menu, parentName, category) {
    const result = [];
    if (menu.children) {
        for (const subMenu of menu
            .children(spreadsheetEnv)
            .sort((a, b) => a.sequence - b.sequence)) {
            if (!subMenu.isVisible(spreadsheetEnv) || !subMenu.isEnabled(spreadsheetEnv)) {
                continue;
            }
            const subMenuName = `${subMenu.name(spreadsheetEnv)}`;
            if (subMenu.execute) {
                const hotkey = subMenu.shortcut;
                result.push({
                    Component: hotkey ? HotkeyCommandItem : DefaultCommandItem,
                    action() {
                        subMenu.execute(spreadsheetEnv);
                    },
                    category: subMenu.id === "insert_link" ? "spreadsheet_insert_link" : category,
                    name: `${parentName} / ${subMenuName}`,
                    props: {
                        hotkey: hotkey.replace("Ctrl", "control"),
                    },
                });
            } else {
                result.push(
                    ...registerCommand(
                        spreadsheetEnv,
                        subMenu,
                        `${parentName} / ${subMenuName}`,
                        category
                    )
                );
            }
        }
    }
    return result;
}
