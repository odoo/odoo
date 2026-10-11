import { registry } from "@web/core/registry";
import { services } from "@web/core/services";
import { CommandPalette } from "./command_palette";
import { DialogPlugin } from "@web/core/dialog/dialog_plugin";
import { HotkeyPlugin } from "@web/core/hotkeys/hotkey_plugin";
import { UIPlugin } from "@web/core/ui/ui_plugin";

import { Component, EventBus, onWillDestroy, Plugin, t, usePlugin, useProps } from "@odoo/owl";

/**
 * @typedef {import("./command_palette").CommandPaletteConfig} CommandPaletteConfig
 * @typedef {import("../hotkeys/hotkey_plugin").HotkeyOptions} HotkeyOptions
 */

/**
 * @typedef {{
 *  name: string;
 *  action: ()=>(void | CommandPaletteConfig);
 *  category?: string;
 *  href?: string;
 *  className?: string;
 * }} Command
 */

/**
 * @typedef {{
 *  category?: string;
 *  isAvailable?: ()=>(boolean);
 *  global?: boolean;
 *  hotkey?: string;
 *  hotkeyOptions?: HotkeyOptions
 * }} CommandOptions
 */

/**
 * @typedef {Command & CommandOptions & {
 *  removeHotkey?: ()=>void;
 * }} CommandRegistration
 */

const commandCategoryRegistry = registry.category("command_categories");
const commandProviderRegistry = registry.category("command_provider");
const commandSetupRegistry = registry.category("command_setup");

class DefaultFooter extends Component {
    static template = "web.DefaultFooter";
    props = useProps({
        switchNamespace: t.function(),
    });
    setup() {
        this.elements = commandSetupRegistry
            .getEntries()
            .map((el) => ({ namespace: el[0], name: el[1].name }))
            .filter((el) => el.name);
    }

    onClick(namespace) {
        this.props.switchNamespace(namespace);
    }
}

export class CommandPlugin extends Plugin {
    /** @private */
    dialog = usePlugin(DialogPlugin);
    /** @private */
    hotkey = usePlugin(HotkeyPlugin);
    /** @private */
    ui = usePlugin(UIPlugin);

    /** @private @type {Map<number, CommandRegistration>} */
    registeredCommands = new Map();
    /** @private */
    nextToken = 0;
    /** @private */
    isPaletteOpened = false;
    /** @private */
    bus = new EventBus();

    setup() {
        const removeHotkey = this.hotkey.add("control+k", this.openMainPalette.bind(this), {
            bypassEditableProtection: true,
            global: true,
        });
        onWillDestroy(removeHotkey);
    }

    /**
     * @param {CommandPaletteConfig} config command palette config merged with default config
     * @param {Function} [onClose] called when the command palette is closed
     * @returns the actual command palette config if the command palette is already open
     */
    openMainPalette(config = {}, onClose) {
        const configByNamespace = {};
        for (const provider of commandProviderRegistry.getAll()) {
            const namespace = provider.namespace || "default";
            if (!configByNamespace[namespace]) {
                configByNamespace[namespace] = {
                    categories: [],
                    categoryNames: {},
                };
            }
        }

        for (const [category, el] of commandCategoryRegistry.getEntries()) {
            const namespace = el.namespace || "default";
            const name = el.name;
            if (namespace in configByNamespace) {
                configByNamespace[namespace].categories.push(category);
                configByNamespace[namespace].categoryNames[category] = name;
            }
        }

        for (const [
            namespace,
            { emptyMessage, debounceDelay, placeholder },
        ] of commandSetupRegistry.getEntries()) {
            if (namespace in configByNamespace) {
                if (emptyMessage) {
                    configByNamespace[namespace].emptyMessage = emptyMessage;
                }
                if (debounceDelay !== undefined) {
                    configByNamespace[namespace].debounceDelay = debounceDelay;
                }
                if (placeholder) {
                    configByNamespace[namespace].placeholder = placeholder;
                }
            }
        }

        config = Object.assign(
            {
                configByNamespace,
                FooterComponent: DefaultFooter,
                providers: commandProviderRegistry.getAll(),
            },
            config
        );
        return this.openPalette(config, onClose);
    }

    /**
     * @param {CommandPaletteConfig} config
     * @param {Function} [onClose] called when the command palette is closed
     */
    openPalette(config, onClose) {
        if (this.isPaletteOpened) {
            this.bus.trigger("SET-CONFIG", config);
            return;
        }

        // Open Command Palette dialog
        this.isPaletteOpened = true;
        this.dialog.add(
            CommandPalette,
            {
                config,
                bus: this.bus,
            },
            {
                onClose: () => {
                    this.isPaletteOpened = false;
                    if (onClose) {
                        onClose();
                    }
                },
            }
        );
    }

    /**
     * @private
     * @param {Command} command
     * @param {CommandOptions} options
     * @returns {number} token
     */
    registerCommand(command, options) {
        if (!command.name || !command.action || typeof command.action !== "function") {
            throw new Error("A Command must have a name and an action function.");
        }
        const registration = Object.assign({}, command, options);
        if (registration.identifier) {
            const commandsArray = Array.from(this.registeredCommands.values());
            const sameName = commandsArray.find((com) => com.name === registration.name);
            if (sameName) {
                if (registration.identifier !== sameName.identifier) {
                    registration.name += ` (${registration.identifier})`;
                    sameName.name += ` (${sameName.identifier})`;
                }
            } else {
                const sameFullName = commandsArray.find(
                    (com) => com.name === registration.name + `(${registration.identifier})`
                );
                if (sameFullName) {
                    registration.name += ` (${registration.identifier})`;
                }
            }
        }
        if (registration.hotkey) {
            const action = async () => {
                const config = await command.action();
                if (!this.isPaletteOpened && config) {
                    this.openPalette(config);
                }
            };
            registration.removeHotkey = this.hotkey.add(registration.hotkey, action, {
                ...options.hotkeyOptions,
                global: registration.global,
                isAvailable: (...args) => {
                    let available = true;
                    if (registration.isAvailable) {
                        available = registration.isAvailable(...args);
                    }
                    if (available && options.hotkeyOptions?.isAvailable) {
                        available = options.hotkeyOptions?.isAvailable(...args);
                    }
                    return available;
                },
            });
        }

        const token = this.nextToken++;
        this.registeredCommands.set(token, registration);
        if (!options.activeElement) {
            // Due to the way elements are mounted in the DOM by Owl (bottom-to-top),
            // we need to wait the next micro task tick to set the context activate
            // element of the subscription.
            Promise.resolve().then(() => {
                registration.activeElement = this.ui.activeElement();
            });
        }

        return token;
    }

    /**
     * Unsubscribes the token corresponding subscription.
     *
     * @private
     * @param {number} token
     */
    unregisterCommand(token) {
        const cmd = this.registeredCommands.get(token);
        if (cmd && cmd.removeHotkey) {
            cmd.removeHotkey();
        }
        this.registeredCommands.delete(token);
    }

    /**
     * @param {string} name
     * @param {()=>(void | CommandPaletteConfig)} action
     * @param {CommandOptions} [options]
     * @returns {() => void}
     */
    add(name, action, options = {}) {
        const token = this.registerCommand({ name, action }, options);
        return () => {
            this.unregisterCommand(token);
        };
    }

    /**
     * @param {HTMLElement} activeElement
     * @returns {Command[]}
     */
    getCommands(activeElement) {
        return [...this.registeredCommands.values()].filter(
            (command) => command.activeElement === activeElement || command.global
        );
    }
}

services.add(CommandPlugin);

/**
 * -----------------------------------------------------------------------------
 * @todo owl3 migration
 * temporary - to remove when all use of the command service are removed
 * -----------------------------------------------------------------------------
 */
export const commandService = {
    dependencies: ["dialog", "hotkey", "ui"],
    start() {
        return usePlugin(CommandPlugin);
    },
};

registry.category("services").add("command", commandService);
