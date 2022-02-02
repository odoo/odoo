/** @odoo-module **/

import { registry } from "@web/core/registry";
import { CommandPaletteDialog } from "./command_palette_dialog";

const { Component, xml } = owl;

/**
 * @typedef {import("./command_palette").CommandPaletteConfig} CommandPaletteConfig
 */

/**
 * @typedef {{
 *  name: string;
 *  action: ()=>(void | CommandPaletteConfig);
 *  category?: string;
 * }} Command
 */

/**
 * @typedef {{
 *  activeElement?: HTMLElement;
 *  category?: string;
 *  global?: boolean;
 *  hotkey?: string;
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
}
DefaultFooter.template = xml`
<span>
    <span class='o_promote'>TIP</span> — search for
    <t t-foreach="elements" t-as="element" t-key="element.namespace">
        <t t-if="!(element_first || element_last)">, </t>
        <t t-if="element_last and !element_first"> and </t>
        <span t-esc="element.namespace" class='o_promote'/><t t-esc="element.name"/>
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

        hotkeyService.add("control+k", openMainPalette, {
            global: true,
        });

        /**
         * @param {CommandPaletteConfig} config command palette config merged with default config
         * @returns the actual command palette config if the command palette is already open
         */
        function openMainPalette(config = {}) {
            const categoriesByNamespace = {};
            commandCategoryRegistry.getEntries().forEach(([category, el]) => {
                const namespace = el.namespace ? el.namespace : "default";
                if (namespace in categoriesByNamespace) {
                    categoriesByNamespace[namespace].push(category);
                } else {
                    categoriesByNamespace[namespace] = [category];
                }
            });

            const emptyMessageByNamespace = {};
            commandSetupRegistry.getEntries().forEach(([key, { emptyMessage }]) => {
                if (emptyMessage) {
                    emptyMessageByNamespace[key] = emptyMessage.toString();
                }
            });
            config = Object.assign(
                {
                    categoriesByNamespace,
                    emptyMessageByNamespace,
                    FooterComponent: DefaultFooter,
                    placeholder: env._t("Search for a command..."),
                    providers: commandProviderRegistry.getAll(),
                },
                config
            );
            return openPalette(config);
        }

        /**
         * @param {CommandPaletteConfig} config
         * @returns config if the command palette is already open
         */
        function openPalette(config) {
            if (isPaletteOpened) {
                return config;
            }

            // Open Command Palette dialog
            isPaletteOpened = true;
            dialog.add(
                CommandPaletteDialog,
                {
                    config,
                },
                {
                    onClose: () => {
                        isPaletteOpened = false;
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
                registration.removeHotkey = hotkeyService.add(
                    registration.hotkey,
                    registration.action,
                    {
                        activeElement: registration.activeElement,
                        global: registration.global,
                    }
                );
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
