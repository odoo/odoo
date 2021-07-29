/** @odoo-module **/

import { isMacOS } from "@web/core/browser/feature_detection";
import { useHotkey } from "@web/core/hotkey_hook";
import { registry } from "@web/core/registry";
import { capitalize } from "@web/core/utils/strings";
import { getVisibleElements } from "@web/core/utils/ui";
import { DefaultCommandItem } from "./command_service";

const { Component } = owl;

class HotkeyCommandItem extends Component {
    setup() {
        if (this.props.hotkey) {
            useHotkey(this.props.hotkey, () => {
                this.props.action();
                this.trigger("close");
            });
        }
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
HotkeyCommandItem.template = "web.hotkeyCommandItem";

const commandProviderRegistry = registry.category("command_provider");
commandProviderRegistry.add("command", {
    provide: (env, options = {}) => {
        const commands = env.services.command.getCommands(options.activeElement);
        return commands.map((command) => ({
            ...command,
            Component: command.hotkey ? HotkeyCommandItem : DefaultCommandItem,
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
                "no description provided";
            commands.push({
                name: capitalize(description.trim().toLowerCase()),
                hotkey: `${overlayModifier}+${el.dataset.hotkey}`,
                action: () => {
                    // AAB: not sure it is enough, we might need to trigger all events that occur when you actually click
                    el.focus();
                    el.click();
                },
                category,
            });
        }
        return commands.map((command) => ({
            ...command,
            Component: HotkeyCommandItem,
        }));
    },
});
