/** @odoo-module **/

import { registry } from "@web/core/registry";
import { CommandPalette } from "./command_palette";

import { Component, xml, EventBus } from "@odoo/owl";

/**
 * @typedef {import("./command_palette").CommandPaletteConfig} CommandPaletteConfig
 */

/**
 * @typedef {{
 *  name: string;
 *  action: ()=>(void | CommandPaletteConfig);
 *  category?: string;
 *  href?: string;
 * }} Command
 */

/**
 * @typedef {import("../hotkeys/hotkey_service").HotkeyOptions & {
 *  category?: string;
 *  isAvailable: ()=>(boolean);
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
DefaultFooter.template = xml`
<span>
    <span class="fw-bolder text-primary">TIP</span> — search for
    <t t-foreach="elements" t-as="element" t-key="element.namespace">
        <t t-if="!(element_first || element_last)">, </t>
        <t t-if="element_last and !element_first"> and </t>
        <span class="o_namespace btn-link text-primary cursor-pointer" t-on-click="() => this.onClick(element.namespace)">
            <span t-out="element.namespace" class="fw-bolder text-primary"/><t t-out="element.name"/>
        </span>
    </t>
</span>
`;

export const commandService = {
    dependencies: ["dialog", "hotkey", "ui"],
    start(env, { dialog, hotkey: hotkeyService, ui }) {
        /** @type {Map<CommandRegistration>} */
        const registeredCommands = new Map();
        let nextToken = 0;
        let isPaletteOpened = false;
        const bus = new EventBus();

        hotkeyService.add("control+k", openMainPalette, {
            bypassEditableProtection: true,
            global: true,
        });

        /**
         * @param {CommandPaletteConfig} config command palette config merged with default config
         * @param {Function} onClose called when the command palette is closed
         * @returns the actual command palette config if the command palette is already open
         */
        function openMainPalette(config = {}, onClose) {
            const configByNamespace = {};
            for (const provider of commandProviderRegistry.getAll()) {
                const namespace = provider.namespace || "default";
                if (!configByNamespace[namespace]) {
                    configByNamespace[namespace] = {
                        categories: [],
                    };
                }
            }

            for (const [category, el] of commandCategoryRegistry.getEntries()) {
                const namespace = el.namespace || "default";
                if (namespace in configByNamespace) {
                    configByNamespace[namespace].categories.push(category);
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
            return openPalette(config, onClose);
        }

        /**
         * @param {CommandPaletteConfig} config
         * @param {Function} onClose called when the command palette is closed
         */
        function openPalette(config, onClose) {
            if (isPaletteOpened) {
                bus.trigger("SET-CONFIG", config);
                return;
            }

            // Open Command Palette dialog
            isPaletteOpened = true;
            dialog.add(
                CommandPalette,
                {
                    config,
                    bus,
                },
                {
                    onClose: () => {
                        isPaletteOpened = false;
                        if (onClose) {
                            onClose();
                        }
                    },
                }
            );
        }

        /**
         * @param {Command} command
         * @param {CommandOptions} options
         * @returns {number} token
         */
        function registerCommand(command, options) {
            if (!command.name || !command.action || typeof command.action !== "function") {
                throw new Error("A Command must have a name and an action function.");
            }

            const registration = Object.assign({}, command, options);
            if (registration.hotkey) {
                const action = async () => {
                    const commandService = env.services.command;
                    const config = await command.action();
                    if (!isPaletteOpened && config) {
                        commandService.openPalette(config);
                    }
                };
                registration.removeHotkey = hotkeyService.add(registration.hotkey, action, {
                    activeElement: registration.activeElement,
                    global: registration.global,
                    validate: registration.isAvailable,
                });
            }

            const token = nextToken++;
            registeredCommands.set(token, registration);
            if (!options.activeElement) {
                // Due to the way elements are mounted in the DOM by Owl (bottom-to-top),
                // we need to wait the next micro task tick to set the context activate
                // element of the subscription.
                Promise.resolve().then(() => {
                    registration.activeElement = ui.activeElement;
                });
            }

            return token;
        }

        /**
         * Unsubscribes the token corresponding subscription.
         *
         * @param {number} token
         */
        function unregisterCommand(token) {
            const cmd = registeredCommands.get(token);
            if (cmd && cmd.removeHotkey) {
                cmd.removeHotkey();
            }
            registeredCommands.delete(token);
        }

        return {
            /**
             * @param {string} name
             * @param {()=>(void | CommandPaletteConfig)} action
             * @param {CommandOptions} [options]
             * @returns {() => void}
             */
            add(name, action, options = {}) {
                const token = registerCommand({ name, action }, options);
                return () => {
                    unregisterCommand(token);
                };
            },
            /**
             * @param {HTMLElement} activeElement
             * @returns {Command[]}
             */
            getCommands(activeElement) {
                return [...registeredCommands.values()].filter(
                    (command) => command.activeElement === activeElement || command.global
                );
            },
            openMainPalette,
            openPalette,
        };
    },
};

registry.category("services").add("command", commandService);
