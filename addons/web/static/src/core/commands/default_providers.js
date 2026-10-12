import { isMacOS } from "@web/core/browser/feature_detection";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { capitalize } from "@web/core/utils/strings";
import { getVisibleElements } from "@web/core/utils/ui";
import { DefaultCommandItem } from "./command_palette";

import { Component, t, useProps, usePlugin } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { HotkeyPlugin } from "@web/core/hotkeys/hotkey_plugin";

const commandSetupRegistry = registry.category("command_setup");
commandSetupRegistry.add("default", {
    emptyMessage: _t("No command found"),
    placeholder: _t("Search for a command..."),
});

export class HotkeyCommandItem extends Component {
    static template = "web.HotkeyCommandItem";
    props = useProps({
        hotkey: t.any(),
        hotkeyOptions: t.any().optional(),
        name: t.any().optional(),
        searchValue: t.any().optional(),
        executeCommand: t.any(),
        slots: t.any(),
    });
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

const commandCategoryRegistry = registry.category("command_categories");
const commandProviderRegistry = registry.category("command_provider");
commandProviderRegistry.add("command", {
    provide(options) {
        const commandService = useService("command");
        const commands = commandService
            .getCommands(options.activeElement)
            .map((cmd) => {
                cmd.category = commandCategoryRegistry.contains(cmd.category)
                    ? cmd.category
                    : "default";
                return cmd;
            })
            .filter((command) => command.isAvailable === undefined || command.isAvailable());
        // Filter out same category dupplicate commands
        const uniqueCommands = commands.filter(
            (obj, index) =>
                index ===
                commands.findIndex((o) => obj.name === o.name && obj.category === o.category)
        );
        return uniqueCommands.map((command) => ({
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
    provide(options) {
        const commands = [];
        const overlayModifier = usePlugin(HotkeyPlugin).overlayModifier;
        // Also retrieve all hotkeyables elements
        for (const el of getVisibleElements(
            options.activeElement,
            "[data-hotkey]:not(:disabled)"
        )) {
            const closest = el.closest("[data-command-category]");
            const category = closest ? closest.dataset.commandCategory : "default";
            if (category === "disabled") {
                continue;
            }

            const description =
                el.title ||
                el.dataset.bsOriginalTitle || // LEGACY: bootstrap moves title to data-bs-original-title
                el.dataset.tooltip ||
                el.placeholder ||
                (el.innerText &&
                    `${el.innerText.slice(0, 50)}${el.innerText.length > 50 ? "..." : ""}`) ||
                _t("no description provided");

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
