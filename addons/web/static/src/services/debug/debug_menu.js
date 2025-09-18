// @ts-check

/** @module @web/services/debug/debug_menu - Extended debug menu with command palette integration */

import { Dropdown } from "@web/components/dropdown/dropdown";
import { DropdownItem } from "@web/components/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { useCommand } from "@web/services/commands/command_hook";
import { DebugMenuBasic } from "@web/services/debug/debug_menu_basic";

import { useEnvDebugContext } from "./debug_context";

/**
 * Extended debug menu that also registers debug tools as a command palette
 * command (Ctrl+K → "Debug tools..."). When invoked from the palette, it
 * loads all debug items and presents them as selectable commands.
 */
export class DebugMenu extends DebugMenuBasic {
    static components = { Dropdown, DropdownItem };
    static props = {};
    setup() {
        super.setup();
        const debugContext = useEnvDebugContext();
        this.command = useService("command");
        useCommand(
            _t("Debug tools..."),
            /** @type {any} */ (
                async () => {
                    const items = await debugContext.getItems(this.env);
                    let index = 0;
                    const defaultCategories = items
                        .filter((/** @type {any} */ item) => item.type === "separator")
                        .map(() => (index += 1));
                    const provider = {
                        async provide() {
                            const categories = [...defaultCategories];
                            let category = categories.shift();
                            const result = [];
                            items.forEach((item) => {
                                if (item.type === "item") {
                                    result.push({
                                        name: item.description.toString(),
                                        action: item.callback,
                                        category,
                                    });
                                } else if (item.type === "separator") {
                                    category = categories.shift();
                                }
                            });
                            return result;
                        },
                    };
                    const configByNamespace = {
                        default: {
                            categories: defaultCategories,
                            emptyMessage: _t("No debug command found"),
                            placeholder: _t("Choose a debug command..."),
                        },
                    };
                    const commandPaletteConfig = {
                        configByNamespace,
                        providers: [provider],
                    };
                    return commandPaletteConfig;
                }
            ),
            {
                category: "debug",
            },
        );
    }
}
