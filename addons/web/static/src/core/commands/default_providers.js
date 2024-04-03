/** @odoo-module **/

import { isMacOS } from "@web/core/browser/feature_detection";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { capitalize } from "@web/core/utils/strings";
import { getVisibleElements } from "@web/core/utils/ui";
import { DefaultCommandItem } from "./command_palette";

import { Component } from "@odoo/owl";

const commandSetupRegistry = registry.category("command_setup");
commandSetupRegistry.add("default", {
    emptyMessage: _lt("No command found"),
    placeholder: _lt("Search for a command..."),
});

export class HotkeyCommandItem extends Component {
    setup() {
        useHotkey(this.props.hotkey, this.props.executeCommand);
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

const commandCategoryRegistry = registry.category("command_categories");
const commandProviderRegistry = registry.category("command_provider");
commandProviderRegistry.add("command", {
    provide: (env, options = {}) => {
        const commands = env.services.command
            .getCommands(options.activeElement)
            .map((cmd) => {
                cmd.category = commandCategoryRegistry.contains(cmd.category)
                    ? cmd.category
                    : "default";
                return cmd;
            })
            .filter((command) => command.isAvailable === undefined || command.isAvailable());

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
                el.dataset.bsOriginalTitle || // LEGACY: bootstrap moves title to data-bs-original-title
                el.dataset.tooltip ||
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
