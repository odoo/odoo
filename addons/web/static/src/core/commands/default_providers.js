/** @odoo-module **/

import { isMacOS } from "@web/core/browser/feature_detection";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { fuzzyLookup } from "@web/core/utils/search";
import { capitalize } from "@web/core/utils/strings";
import { getVisibleElements } from "@web/core/utils/ui";
import { DefaultCommandItem } from "./command_palette";

const { Component } = owl;

export class HotkeyCommandItem extends Component {
    setup() {
        useHotkey(this.props.hotkey, () => {
            this.trigger("execute-command");
        });
    }

    getKeysToPress(command) {
        const { hotkey } = command;
        let result = hotkey.split("+");
        if (isMacOS()) {
            result = result
                .map((x) => x.replace("control", "command"))
                .map((x) => x.replace("alt", "control"));
        }
        return result.map((key) => key.toUpperCase());
    }
}
HotkeyCommandItem.template = "web.HotkeyCommandItem";
const commandEmptyMessageRegistry = registry.category("command_empty_list");
commandEmptyMessageRegistry.add("default", _lt("No commands found"));

const commandCategoryRegistry = registry.category("command_categories");

const commandProviderRegistry = registry.category("command_provider");
commandProviderRegistry.add("command", {
    provide: (env, options = {}) => {
        const commands = env.services.command.getCommands(options.activeElement).map((cmd) => {
            cmd.category = commandCategoryRegistry.contains(cmd.category)
                ? cmd.category
                : "default";
            return cmd;
        });

        return commands.map((command) => ({
            Component: command.hotkey ? HotkeyCommandItem : DefaultCommandItem,
            action: command.action,
            category: command.category,
            name: command.name,
            props: {
                hotkey: command.hotkey,
                hotkeyOptions: command.hotkeyOptions,
            },
        }));
    },
});

commandProviderRegistry.add("data-hotkeys", {
    provide: (env, options = {}) => {
        const commands = [];
        const overlayModifier = registry.category("services").get("hotkey").overlayModifier;
        // Also retrieve all hotkeyables elements
        for (const el of getVisibleElements(
            options.activeElement,
            "[data-hotkey]:not(:disabled)"
        )) {
            const closest = el.closest("[data-command-category]");
            const category = closest ? closest.dataset.commandCategory : "default";

            const description =
                el.title ||
                el.dataset.originalTitle || // LEGACY: bootstrap moves title to data-original-title
                el.placeholder ||
                (el.innerText &&
                    `${el.innerText.slice(0, 50)}${el.innerText.length > 50 ? "..." : ""}`) ||
                env._t("no description provided");

            commands.push({
                Component: HotkeyCommandItem,
                action: () => {
                    // AAB: not sure it is enough, we might need to trigger all events that occur when you actually click
                    el.focus();
                    el.click();
                },
                category,
                name: capitalize(description.trim().toLowerCase()),
                props: {
                    hotkey: `${overlayModifier}+${el.dataset.hotkey}`,
                },
            });
        }
        return commands;
    },
});

commandProviderRegistry.add("test", {
    namespace: "!",
    provide: async (env, options) => {
        let result = await env.services.orm.searchRead("ir.model", [], ["name", "model", "id"]);
        result = options.searchValue
            ? fuzzyLookup(options.searchValue, result, (r) => r.name)
            : result;
        return result.map((r) => ({
            name: `${r.name} (${r.model})`,
            action: async () => {
                const provider = {
                    provide: async (env, options) => {
                        const ir_model = r.model;
                        const result = await env.services.orm.searchRead(
                            ir_model,
                            [["name", "ilike", `${options.searchValue}`]],
                            ["name", "id"]
                        );
                        return result.map((r) => ({
                            name: r.name,
                            action: () => {
                                env.services.action.doAction({
                                    name: r.name,
                                    res_id: r.id,
                                    res_model: ir_model,
                                    type: "ir.actions.act_window",
                                    views: [[false, "form"]],
                                });
                            },
                        }));
                    },
                };
                const commandPaletteConfig = {
                    emptyMessageByNamespace: { default: `No ${r.name} found` },
                    placeholder: env._t("Choose a debug command..."),
                    providers: [provider],
                };
                return commandPaletteConfig;
            },
        }));
    },
});
