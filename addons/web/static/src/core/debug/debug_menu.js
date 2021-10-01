/** @odoo-module **/

import { useCommand } from "@web/core/commands/command_hook";
import { useService } from "@web/core/utils/hooks";
import { useEnvDebugContext } from "./debug_context";

const { Component } = owl;

export class DebugMenu extends Component {
    setup() {
        const debugContext = useEnvDebugContext();
        // Needs to be bound to this for use in template
        this.getElements = async () => {
            this.elements = await debugContext.getItems(this.env);
        };
        this.command = useService("command");
        useCommand(
            this.env._t("Debug tools..."),
            async () => {
                const items = await debugContext.getItems(this.env);
                let index = 0;
                const defaultCategories = items
                    .filter((item) => item.type === "separator")
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
                const commandPaletteConfig = {
                    categoriesByNamespace: {
                        default: defaultCategories,
                    },
                    emptyMessageByNamespace: { default: this.env._t("No commands found") },
                    placeholder: this.env._t("Choose a debug command..."),
                    providers: [provider],
                };
                return this.command.openPalette(commandPaletteConfig);
            },
            {
                category: "debug",
            }
        );
    }
}
DebugMenu.template = "web.DebugMenu";
