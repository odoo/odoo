/** @odoo-module **/

import { useAutofocus, useService } from "@web/core/utils/hooks";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { registry } from "@web/core/registry";
import { KeepLast } from "@web/core/utils/concurrency";
import { scrollTo } from "@web/core/utils/scrolling";
import { fuzzyLookup } from "@web/core/utils/search";
import { debounce } from "@web/core/utils/timing";

const { Component, hooks } = owl;
const { useRef, useState } = hooks;

const DEFAULT_PLACEHOLDER = "Search for an action...";
const FUZZY_SEARCH = ["__default__"];

const commandCategoryRegistry = registry.category("command_categories");
const commandProviderRegistry = registry.category("command_provider");

/**
 * @typedef {import("./command_service").Command} Command
 */

/**
 * Util used to filter commands that are within category.
 * Note: for the default category, also get all commands having invalid category.
 *
 * @param {string} categoryName the category key
 * @returns an array filter predicate
 */
function commandsWithinCategory(categoryName) {
    return (cmd) => {
        const inCurrentCategory = categoryName === cmd.category;
        const fallbackCategory =
            categoryName === "default" && !commandCategoryRegistry.contains(cmd.category);
        return inCurrentCategory || fallbackCategory;
    };
}

export class DefaultCommandItem extends Component {}
DefaultCommandItem.template = "web.defaultCommandItem";

export class CommandPalette extends Component {
    setup() {
        this.keyId = 1;
        this.displayByCategory = true;
        this.keepLast = new KeepLast();
        this.DefaultCommandItem = DefaultCommandItem;
        this.activeElement = useService("ui").activeElement;
        this.searchBar = useRef("search_bar");
        this.onDebouncedSearchInput = debounce(this.onSearchInput, 250);

        useAutofocus();

        useHotkey("Enter", () => this.executeSelectedCommand());
        useHotkey("ArrowUp", () => this.selectCommandAndScrollTo("PREV"), { allowRepeat: true });
        useHotkey("ArrowDown", () => this.selectCommandAndScrollTo("NEXT"), { allowRepeat: true });

        /**
         * @type {{commands: Command[], selectedCommand: Command, placeHolder: String}}
         */
        this.state = useState({
            commands: [],
            selectedCommand: -1,
            placeHolder: DEFAULT_PLACEHOLDER,
        });

        const mainProviders = { __default__: [] };
        for (const provider of commandProviderRegistry.getAll()) {
            const nameSpace = provider.nameSpace || "__default__";
            if (nameSpace in mainProviders) {
                mainProviders[nameSpace] = mainProviders[nameSpace].concat([provider]);
            } else {
                mainProviders[nameSpace] = [provider];
            }
        }
        this.providerStack = [mainProviders];

        this.setCommands("__default__", {
            activeElement: this.activeElement,
        });
    }

    get categories() {
        const categories = [];
        if (this.displayByCategory) {
            for (const [key, value] of commandCategoryRegistry.getEntries()) {
                const commands = this.state.commands.filter(commandsWithinCategory(key));
                if (commands.length) {
                    categories.push({
                        commands,
                        keyId: key,
                        ...value,
                    });
                }
            }
        } else {
            const commands = this.state.commands;
            if (commands.length) {
                categories.push({
                    commands,
                    keyId: "default",
                    label: "",
                });
            }
        }
        return categories;
    }

    get lastProvider() {
        return this.providerStack[this.providerStack.length - 1];
    }

    async setCommands(key, options = {}) {
        const proms = this.lastProvider[key].map((provider) => {
            const { provide } = provider;
            const result = provide(this.env, options);
            return result;
        });
        let commands = (await this.keepLast.add(Promise.all(proms))).flatMap(
            (commands) => commands
        );

        if (options.searchValue && FUZZY_SEARCH.includes(key)) {
            this.displayByCategory = false;
            commands = fuzzyLookup(options.searchValue, commands, (c) => c.name);
        } else {
            this.displayByCategory = true;
            // we have to sort the commands by category to avoid navigation issues with the arrows
            let commandsSorted = [];
            for (const [key, _] of commandCategoryRegistry.getEntries()) {
                const commandsByCategory = commands.filter(commandsWithinCategory(key));
                commandsSorted = commandsSorted.concat(commandsByCategory);
            }
            commands = commandsSorted;
        }

        this.state.commands = commands.map((command) => ({
            ...command,
            keyId: this.keyId++,
        }));
        this.selectCommand(this.state.commands.length ? 0 : -1);
        this.mouseSelectionActive = false;
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
        let nextIndex;
        if (type === "NEXT") {
            nextIndex = index < this.state.commands.length - 1 ? index + 1 : 0;
        } else if (type === "PREV") {
            nextIndex = index > 0 ? index - 1 : this.state.commands.length - 1;
        }
        this.selectCommand(nextIndex);

        const listbox = this.el.querySelector(".o_command_palette_listbox");
        const command = listbox.querySelector(`#o_command_${nextIndex}`);
        scrollTo(command.children[0], listbox);
    }

    onCommandClicked(index) {
        this.selectCommand(index);
        this.executeSelectedCommand();
    }

    async executeSelectedCommand() {
        if (this.state.selectedCommand) {
            const result = await this.state.selectedCommand.action();
            if (result) {
                const { placeHolder, provide } = result;
                this.providerStack.push({ __default__: [{ provide }] });
                this.setCommands("__default__", {
                    activeElement: this.activeElement,
                });
                this.state.placeHolder = placeHolder || DEFAULT_PLACEHOLDER;
                this.searchBar.el.value = "";
            } else {
                this.props.closeMe();
            }
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
        let searchValue = ev.target.value;
        let key = "__default__";
        if (searchValue.length && searchValue[0] in this.lastProvider) {
            key = searchValue[0];
            searchValue = searchValue.slice(1);
        }
        this.setCommands(key, {
            searchValue,
            activeElement: this.activeElement,
        });
    }
}
CommandPalette.template = "web.CommandPalette";
