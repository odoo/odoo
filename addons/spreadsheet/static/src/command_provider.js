import { registries } from "@odoo/o-spreadsheet";
import { useEffect, useEnv } from "@odoo/owl";
import { registry } from "@web/core/registry";

const { topbarMenuRegistry } = registries;
const commandProviderRegistry = registry.category("command_provider");
const commandCategoryRegistry = registry.category("command_categories");

/**
 * Activate the command palette for spreadsheet.
 */
export function useSpreadsheetCommandPalette() {
    const env = useEnv();
    useEffect(
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
                result.push({
                    action() {
                        subMenu.execute(spreadsheetEnv);
                    },
                    category: subMenu.id === "insert_link" ? "spreadsheet_insert_link" : category,
                    name: `${parentName} / ${subMenuName}`,
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
