/** @odoo-module **/

import { registry } from "@web/core/registry";
import { CommandPaletteDialog } from "./command_palette_dialog";

const { xml } = owl.tags;

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
const commandEmptyMessageRegistry = registry.category("command_empty_list");
const commandProviderRegistry = registry.category("command_provider");

const footerTemplate = xml`
<span>
    <span class='o_promote'>TIP</span> — search for <span class='o_promote'>@</span>users, <span class='o_promote'>#</span>channels, and <span class='o_promote'>/</span>menus
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
            bypassEditableProtection: true,
            global: true,
        });

        function openMainPalette() {
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
            commandEmptyMessageRegistry.getEntries().forEach(([key, message]) => {
                emptyMessageByNamespace[key] = message.toString();
            });

            const config = {
                categoriesByNamespace,
                emptyMessageByNamespace,
                footerTemplate,
                placeholder: env._t("Search for a command..."),
                providers: commandProviderRegistry.getAll(),
            };
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
            openPalette,
        };
    },
};

registry.category("services").add("command", commandService);
