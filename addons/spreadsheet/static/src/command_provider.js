/** @odoo-module native */
import { registries } from "@odoo/o-spreadsheet";
import { useEffect, useEnv } from "@odoo/owl";
import { AUTHORIZED_KEYS, MODIFIERS } from "@web/core/browser/hotkeys";
import { registry } from "@web/core/registry";
import { HotkeyCommandItem } from "@web/ui/commands";

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
        () => [],
    );
}

function setupSpreadsheetCategories(spreadsheetEnv) {
    let sequence = 5;
    commandCategoryRegistry.add(
        "spreadsheet_insert_link",
        {},
        { sequence: 0, force: true },
    );
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

/**
 * o-spreadsheet stores a menu item's keyboard shortcut in its `description`
 * ("Ctrl+C", "Ctrl+Shift+V"), which it renders to the right of the item in the
 * topbar menus. Turn that into a hotkey the command palette can register, or
 * "" when it is not one our hotkey service accepts -- `useHotkey` throws on an
 * unauthorized key, which would take the whole palette down with it.
 *
 * @param {string} description
 * @returns {string}
 */
function toHotkey(description) {
    if (!description) {
        return "";
    }
    const hotkey = description.toLowerCase().replace("ctrl", "control");
    const keys = hotkey.split("+").filter((key) => !MODIFIERS.includes(key));
    return keys.length === 1 && AUTHORIZED_KEYS.includes(keys[0]) ? hotkey : "";
}

function registerCommand(spreadsheetEnv, menu, parentName, category) {
    const result = [];
    if (menu.children) {
        for (const subMenu of menu
            .children(spreadsheetEnv)
            .sort((a, b) => a.sequence - b.sequence)) {
            if (
                !subMenu.isVisible(spreadsheetEnv) ||
                !subMenu.isEnabled(spreadsheetEnv)
            ) {
                continue;
            }
            const subMenuName = `${subMenu.name(spreadsheetEnv)}`;
            if (subMenu.execute) {
                const hotkey = toHotkey(subMenu.description(spreadsheetEnv));
                result.push({
                    action() {
                        subMenu.execute(spreadsheetEnv);
                    },
                    category:
                        subMenu.id === "insert_link"
                            ? "spreadsheet_insert_link"
                            : category,
                    name: `${parentName} / ${subMenuName}`,
                    // The palette falls back to `DefaultCommandItem` on its
                    // own, so only say something when there is a shortcut.
                    ...(hotkey && {
                        Component: HotkeyCommandItem,
                        props: { hotkey },
                    }),
                });
            } else {
                result.push(
                    ...registerCommand(
                        spreadsheetEnv,
                        subMenu,
                        `${parentName} / ${subMenuName}`,
                        category,
                    ),
                );
            }
        }
    }
    return result;
}
