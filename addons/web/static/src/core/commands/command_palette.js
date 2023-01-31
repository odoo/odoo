/** @odoo-module **/

import { useAutofocus, useService } from "@web/core/utils/hooks";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { KeepLast } from "@web/core/utils/concurrency";
import { scrollTo } from "@web/core/utils/scrolling";
import { fuzzyLookup } from "@web/core/utils/search";
import { debounce } from "@web/core/utils/timing";
import { _lt } from "@web/core/l10n/translation";

const { Component, hooks } = owl;
const { useState } = hooks;

const DEFAULT_PLACEHOLDER = _lt("Search...");
const DEFAULT_EMPTY_MESSAGE = _lt("No results found");
const FUZZY_NAMESPACES = ["default"];

/**
 * @typedef {import("./command_service").Command} Command
 */

/**
 * @typedef {Command & {
 *  Component?: owl.Component;
 *  props?: object;
 * }} CommandItem
 */

/**
 * @typedef {{
 *  namespace?: string;
 *  provide: ()=>CommandItem[];
 * }} Provider
 */

/**
 * @typedef {{
 *  categoriesByNamespace?: {[namespace]: string[]};
 *  namespace?: string;
 *  emptyMessageByNamespace?: {[namespace]: string};
 *  footerTemplate?: string;
 *  placeholder?: string;
 *  providers: Provider[];
 * }} CommandPaletteConfig
 */

/**
 * Util used to filter commands that are within category.
 * Note: for the default category, also get all commands having invalid category.
 *
 * @param {string} categoryName the category key
 * @param {string[]} categories
 * @returns an array filter predicate
 */
function commandsWithinCategory(categoryName, categories) {
    return (cmd) => {
        const inCurrentCategory = categoryName === cmd.category;
        const fallbackCategory = categoryName === "default" && !categories.includes(cmd.category);
        return inCurrentCategory || fallbackCategory;
    };
}

export class DefaultCommandItem extends Component {}
DefaultCommandItem.template = "web.DefaultCommandItem";

export class CommandPalette extends Component {
    setup() {
        this.keyId = 1;
        this.keepLast = new KeepLast();
        this._sessionId = CommandPalette.lastSessionId++;
        this.DefaultCommandItem = DefaultCommandItem;
        this.activeElement = useService("ui").activeElement;
        const onDebouncedSearchInput = debounce.apply(this, [this.onSearchInput, 200]);
        this.onDebouncedSearchInput = (...args) => {
            this.inputPromise = onDebouncedSearchInput.apply(this, args).catch(() => {
                this.inputPromise = null;
            });
        };

        useAutofocus();

        useHotkey("Enter", () => this.executeSelectedCommand(), { bypassEditableProtection: true });
        useHotkey("ArrowUp", () => this.selectCommandAndScrollTo("PREV"), {
            bypassEditableProtection: true,
            allowRepeat: true,
        });
        useHotkey("ArrowDown", () => this.selectCommandAndScrollTo("NEXT"), {
            bypassEditableProtection: true,
            allowRepeat: true,
        });

        /**
         * @type {{ commands: CommandItem[],
         *          emptyMessage: string,
         *          footerTemplate: string,
         *          placeholder: string,
         *          searchValue: string,
         *          selectedCommand: CommandItem }}
         */
        this.state = useState({
            commands: [],
        });

        this.setCommandPaletteConfig(this.props.config);
    }

    get commandsByCategory() {
        const categories = [];
        for (const category of this.categoryKeys) {
            const commands = this.state.commands.filter(
                commandsWithinCategory(category, this.categoryKeys)
            );
            if (commands.length) {
                categories.push({
                    commands,
                    keyId: category,
                });
            }
        }
        return categories;
    }

    /**
     * Apply the new config to the command pallet
     * @param {CommandPaletteConfig} config
     */
    setCommandPaletteConfig(config) {
        const result = { default: [] };
        for (const provider of config.providers) {
            const namespace = provider.namespace || "default";
            if (namespace in result) {
                result[namespace].push(provider);
            } else {
                result[namespace] = [provider];
            }
        }
        this.categoriesByNamespace = config.categoriesByNamespace;
        this.emptyMessageByNamespace = config.emptyMessageByNamespace || {};
        this.providersByNamespace = result;

        this.state.footerTemplate = config.footerTemplate;

        this.state.placeholder = config.placeholder || DEFAULT_PLACEHOLDER.toString();

        const namespace = config.namespace || "default";
        this.setCommands(namespace, {
            activeElement: this.activeElement,
            searchValue: "",
            sessionId: this._sessionId,
        });
        this.state.searchValue = namespace === "default" ? "" : namespace;
    }

    /**
     * Modifies the commands to be displayed according to the namespace and the options.
     * Selects the first command in the new list.
     * @param {string} namespace
     * @param {object} options
     */
    async setCommands(namespace, options = {}) {
        this.categoryKeys = ["default"];
        const proms = this.providersByNamespace[namespace].map((provider) => {
            const { provide } = provider;
            const result = provide(this.env, options);
            return result;
        });
        let commands = (await this.keepLast.add(Promise.all(proms))).flat();
        if (options.searchValue && FUZZY_NAMESPACES.includes(namespace)) {
            commands = fuzzyLookup(options.searchValue, commands, (c) => c.name);
        } else {
            // we have to sort the commands by category to avoid navigation issues with the arrows
            if (this.categoriesByNamespace && this.categoriesByNamespace[namespace]) {
                let commandsSorted = [];
                this.categoryKeys = this.categoriesByNamespace[namespace];
                if (!this.categoryKeys.includes("default")) {
                    this.categoryKeys.push("default");
                }
                for (const category of this.categoryKeys) {
                    commandsSorted = commandsSorted.concat(
                        commands.filter(commandsWithinCategory(category, this.categoryKeys))
                    );
                }
                commands = commandsSorted;
            }
        }

        this.state.commands = commands.map((command) => ({
            ...command,
            keyId: this.keyId++,
        }));
        this.selectCommand(this.state.commands.length ? 0 : -1);
        this.mouseSelectionActive = false;
        this.state.emptyMessage =
            this.emptyMessageByNamespace[namespace] || DEFAULT_EMPTY_MESSAGE.toString();
    }

    selectCommand(index) {
        if (index === -1 || index >= this.state.commands.length) {
            this.state.selectedCommand = null;
            return;
        }
        this.state.selectedCommand = this.state.commands[index];
    }

    selectCommandAndScrollTo(type) {
        // In case the mouse is on the palette command, it avoids the selection
        // of a command caused by a scroll.
        this.mouseSelectionActive = false;
        const index = this.state.commands.indexOf(this.state.selectedCommand);
        if (index === -1) {
            return;
        }
        let nextIndex;
        if (type === "NEXT") {
            nextIndex = index < this.state.commands.length - 1 ? index + 1 : 0;
        } else if (type === "PREV") {
            nextIndex = index > 0 ? index - 1 : this.state.commands.length - 1;
        }
        this.selectCommand(nextIndex);

        const listbox = this.el.querySelector(".o_command_palette_listbox");
        const command = listbox.querySelector(`#o_command_${nextIndex}`);
        scrollTo(command, { scrollable: listbox });
    }

    onCommandClicked(index) {
        this.selectCommand(index);
        this.executeSelectedCommand();
    }

    /**
     * Execute the action related to the order.
     * If this action returns a config, then we will use it in the command palette,
     * otherwise we close the command palette.
     * @param {CommandItem} command
     */
    async executeCommand(command) {
        const config = await command.action();
        if (config) {
            this.setCommandPaletteConfig(config);
        } else {
            this.props.closeMe();
        }
    }

    async executeSelectedCommand() {
        await this.inputPromise;
        if (this.state.selectedCommand) {
            this.executeCommand(this.state.selectedCommand);
        }
    }

    onCommandMouseEnter(index) {
        if (this.mouseSelectionActive) {
            this.selectCommand(index);
        } else {
            this.mouseSelectionActive = true;
        }
    }

    async onSearchInput(ev) {
        this.state.searchValue = ev.target.value;
        let searchValue = this.state.searchValue;
        let namespace = "default";
        if (searchValue.length && searchValue[0] in this.providersByNamespace) {
            namespace = searchValue[0];
            searchValue = searchValue.slice(1);
        }
        await this.setCommands(namespace, {
            searchValue,
            activeElement: this.activeElement,
            sessionId: this._sessionId,
        });
    }
}
CommandPalette.lastSessionId = 0;
CommandPalette.template = "web.CommandPalette";
