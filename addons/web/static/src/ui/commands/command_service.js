// @ts-check
/** @odoo-module native */

import { EventBus } from "@odoo/owl";
import { makeLogger } from "@web/core/debug/debug_logger";
import { CommandPaletteEvent } from "@web/core/events";
import { registry } from "@web/core/registry";

import { DefaultFooter } from "./command_items.js";
import { CommandPalette } from "./command_palette.js";

/** @import { CommandPaletteConfig } from "./command_palette.js" */

/** @import { HotkeyOptions } from "@web/core/hotkeys/hotkey_service" */

/**
 * @typedef {{
 * name: string;
 * action: ()=>(void | CommandPaletteConfig | Promise<void | CommandPaletteConfig>);
 * category?: string;
 * href?: string;
 * className?: string;
 * }} Command
 */

/**
 * @typedef {{
 * category?: string;
 * isAvailable?: (...args: any[]) => boolean;
 * global?: boolean;
 * hotkey?: string;
 * hotkeyOptions?: HotkeyOptions;
 * activeElement?: HTMLElement;
 * scope?: () => Document | HTMLElement;
 * identifier?: string;
 * href?: string;
 * className?: string;
 * }} CommandOptions
 */

/**
 * @typedef {Command & CommandOptions & {
 * removeHotkey?: ()=>void;
 * getScope: () => Document | HTMLElement;
 * }} CommandRegistration
 */

const commandCategoryRegistry = registry.category("command_categories");
const commandProviderRegistry = registry.category("command_provider");
const commandSetupRegistry = registry.category("command_setup");

commandProviderRegistry.addValidation({
    provide: Function,
    namespace: { type: String, optional: true },
    "*": true,
});

commandCategoryRegistry.addValidation({
    namespace: { type: String, optional: true },
    name: { type: [String, Object], optional: true },
    "*": true,
});

commandSetupRegistry.addValidation({
    debounceDelay: { type: Number, optional: true },
    emptyMessage: { type: [String, Object], optional: true },
    name: { type: [String, Object], optional: true },
    placeholder: { type: [String, Object], optional: true },
    "*": true,
});

const log = makeLogger("web.command");

class CommandService {
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {{ dialog: any, hotkey: any, ui: any }} services
     */
    constructor(env, { dialog, hotkey: hotkeyService, ui }) {
        this.env = env;
        this.dialog = dialog;
        this.hotkeyService = hotkeyService;
        this.ui = ui;
        /** @type {Map<number, CommandRegistration>} */
        this.registeredCommands = new Map();
        /** @type {Record<string, any> | null} */
        this._configByNamespace = null;
        this.configRegistries = [
            commandProviderRegistry,
            commandCategoryRegistry,
            commandSetupRegistry,
        ];
        this.invalidateConfig = () => {
            this._configByNamespace = null;
        };
        for (const reg of this.configRegistries) {
            reg.addEventListener("UPDATE", this.invalidateConfig);
        }
        this.nextToken = 0;
        this.isPaletteOpened = false;
        /** @type {Function | undefined} */
        this.currentOnClose = undefined;
        this.bus = new EventBus();

        this.removeMainPaletteHotkey = hotkeyService.add(
            "control+k",
            () => this.openMainPalette(),
            {
                bypassEditableProtection: true,
                global: true,
            },
        );
    }

    /**
     * @param {Partial<CommandPaletteConfig>} [config]
     * @param {Function} [onClose]
     */
    openMainPalette(config = {}, onClose) {
        const providers = commandProviderRegistry.getAll();
        log.logic("openMainPalette", () => ({
            providers: providers.length,
            searchValue: config.searchValue,
        }));
        this._configByNamespace ??= this._buildConfigByNamespace(providers);
        const mainConfig = {
            configByNamespace: this._configByNamespace,
            FooterComponent: DefaultFooter,
            providers,
            ...config,
        };
        return this.openPalette(mainConfig, onClose);
    }

    /**
     * @param {ReturnType<typeof commandProviderRegistry.getAll>} providers
     * @returns {Record<string, any>}
     */
    _buildConfigByNamespace(providers) {
        /** @type {Record<string, any>} */
        const configByNamespace = {};
        for (const provider of providers) {
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

        return configByNamespace;
    }

    /**
     * @param {CommandPaletteConfig} config
     * @param {Function} [onClose]
     */
    openPalette(config, onClose) {
        if (this.isPaletteOpened) {
            if (onClose) {
                const previousOnClose = this.currentOnClose;
                this.currentOnClose = () => {
                    try {
                        previousOnClose?.();
                    } finally {
                        onClose();
                    }
                };
            }
            this.bus.trigger(CommandPaletteEvent.SET_CONFIG, config);
            return;
        }

        this.isPaletteOpened = true;
        this.currentOnClose = onClose;
        this.dialog.add(
            CommandPalette,
            {
                config,
                bus: this.bus,
            },
            {
                onClose: () => {
                    this.isPaletteOpened = false;
                    const onCloseCallback = this.currentOnClose;
                    this.currentOnClose = undefined;
                    onCloseCallback?.();
                },
            },
        );
    }

    /**
     * @param {Command} command
     * @param {CommandOptions} options
     * @returns {number}
     */
    registerCommand(command, options) {
        if (!command.name || !command.action || typeof command.action !== "function") {
            throw new Error("A Command must have a name and an action function.");
        }
        log.lifecycle("registerCommand", () => ({
            name: command.name,
            category: options?.category,
            hotkey: options?.hotkey,
            global: options?.global,
        }));
        /** @type {CommandRegistration} */
        const registration = /** @type {any} */ ({
            ...command,
            ...options,
        });
        if (registration.hotkey) {
            const action = async () => {
                const config = await command.action();
                if (!this.isPaletteOpened && config) {
                    this.openPalette(config);
                }
            };
            registration.removeHotkey = this.hotkeyService.add(
                registration.hotkey,
                action,
                {
                    ...options.hotkeyOptions,
                    global: registration.global,
                    isAvailable: (/** @type {any[]} */ ...args) =>
                        (!registration.isAvailable ||
                            registration.isAvailable(...args)) &&
                        (!options.hotkeyOptions?.isAvailable ||
                            options.hotkeyOptions.isAvailable(
                                .../** @type {[any]} */ (args),
                            )),
                },
            );
        }

        const captured = options.activeElement ?? this.ui.activeElement;
        registration.getScope = options.scope ?? (() => captured);

        const token = this.nextToken++;
        this.registeredCommands.set(token, registration);
        return token;
    }

    /** @param {number} token */
    unregisterCommand(token) {
        const cmd = this.registeredCommands.get(token);
        if (cmd?.removeHotkey) {
            cmd.removeHotkey();
        }
        this.registeredCommands.delete(token);
    }

    /**
     * @param {string} name
     * @param {()=>(void | CommandPaletteConfig | Promise<void | CommandPaletteConfig>)} action
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
     * @param {Document | HTMLElement} activeElement
     * @returns {Command[]}
     */
    getCommands(activeElement) {
        const commands = [...this.registeredCommands.values()].filter(
            (command) => command.getScope() === activeElement || command.global,
        );
        /** @type {Map<string, CommandRegistration[]>} */
        const byName = new Map();
        for (const command of commands) {
            const group = byName.get(command.name);
            if (group) {
                group.push(command);
            } else {
                byName.set(command.name, [command]);
            }
        }
        return commands.map((command) => {
            if (!command.identifier) {
                return command;
            }
            const group = byName.get(command.name) ?? [];
            if (group.some((c) => c.identifier !== command.identifier)) {
                return {
                    ...command,
                    name: `${command.name} (${command.identifier})`,
                };
            }
            return command;
        });
    }

    destroy() {
        for (const reg of this.configRegistries) {
            reg.removeEventListener("UPDATE", this.invalidateConfig);
        }
        this._configByNamespace = null;
        log.lifecycle("destroy");
        this.removeMainPaletteHotkey();
        for (const token of [...this.registeredCommands.keys()]) {
            this.unregisterCommand(token);
        }
        this.currentOnClose = undefined;
        this.isPaletteOpened = false;
    }
}

export const commandService = {
    dependencies: ["dialog", "hotkey", "ui"],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {{ dialog: any, hotkey: any, ui: any }} services
     * @returns {CommandService}
     */
    start(env, services) {
        return new CommandService(env, services);
    },
};

registry.category("services").add("command", /** @type {any} */ (commandService));
