/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { _lt } from "@web/core/l10n/translation";
import { KeepLast } from "@web/core/utils/concurrency";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { scrollTo } from "@web/core/utils/scrolling";
import { fuzzyLookup } from "@web/core/utils/search";
import { debounce } from "@web/core/utils/timing";
import { isMacOS, isMobileOS } from "@web/core/browser/feature_detection";
import { escapeRegExp } from "@web/core/utils/strings";

import {
    Component,
    onWillStart,
    onWillDestroy,
    useRef,
    useState,
    markRaw,
    useExternalListener,
} from "@odoo/owl";

const DEFAULT_PLACEHOLDER = _lt("Search...");
const DEFAULT_EMPTY_MESSAGE = _lt("No result found");
const FUZZY_NAMESPACES = ["default"];

/**
 * @typedef {import("./command_service").Command} Command
 */

/**
 * @typedef {Command & {
 *  Component?: Component;
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
 *  categories: string[];
 *  debounceDelay: number;
 *  emptyMessage: string;
 *  placeholder: string;
 * }} NamespaceConfig
 */

/**
 * @typedef {{
 *  configByNamespace?: {[namespace: string]: NamespaceConfig};
 *  FooterComponent?: Component;
 *  providers: Provider[];
 *  searchValue?: string;
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

export function splitCommandName(name, searchValue) {
    if (name) {
        const splitName = name.split(new RegExp(`(${escapeRegExp(searchValue)})`, "ig"));
        return searchValue.length && splitName.length > 1 ? splitName : [name];
    }
    return [];
}

export class DefaultCommandItem extends Component {}
DefaultCommandItem.template = "web.DefaultCommandItem";

export class CommandPalette extends Component {
    setup() {
        if (this.props.bus) {
            const setConfig = ({ detail }) => this.setCommandPaletteConfig(detail);
            this.props.bus.addEventListener(`SET-CONFIG`, setConfig);
            onWillDestroy(() => this.props.bus.removeEventListener(`SET-CONFIG`, setConfig));
        }

        this.keyId = 1;
        this.keepLast = new KeepLast();
        this._sessionId = CommandPalette.lastSessionId++;
        this.DefaultCommandItem = DefaultCommandItem;
        this.activeElement = useService("ui").activeElement;
        this.inputRef = useAutofocus();

        useHotkey("Enter", () => this.executeSelectedCommand(), { bypassEditableProtection: true });
        useHotkey("Control+Enter", () => this.executeSelectedCommand(true), {
            bypassEditableProtection: true,
        });
        useHotkey("ArrowUp", () => this.selectCommandAndScrollTo("PREV"), {
            bypassEditableProtection: true,
            allowRepeat: true,
        });
        useHotkey("ArrowDown", () => this.selectCommandAndScrollTo("NEXT"), {
            bypassEditableProtection: true,
            allowRepeat: true,
        });
        useExternalListener(window, "mousedown", this.onWindowMouseDown);

        /**
         * @type {{ commands: CommandItem[],
         *          emptyMessage: string,
         *          FooterComponent: Component,
         *          namespace: string,
         *          placeholder: string,
         *          searchValue: string,
         *          selectedCommand: CommandItem }}
         */
        this.state = useState({});

        this.root = useRef("root");
        this.listboxRef = useRef("listbox");

        onWillStart(() => this.setCommandPaletteConfig(this.props.config));
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
    async setCommandPaletteConfig(config) {
        this.configByNamespace = config.configByNamespace || {};
        this.state.FooterComponent = config.FooterComponent;

        this.providersByNamespace = { default: [] };
        for (const provider of config.providers) {
            const namespace = provider.namespace || "default";
            if (namespace in this.providersByNamespace) {
                this.providersByNamespace[namespace].push(provider);
            } else {
                this.providersByNamespace[namespace] = [provider];
            }
        }

        const { namespace, searchValue } = this.processSearchValue(config.searchValue || "");
        this.switchNamespace(namespace);
        await this.search(searchValue);
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
        const namespaceConfig = this.configByNamespace[namespace] || {};
        if (options.searchValue && FUZZY_NAMESPACES.includes(namespace)) {
            commands = fuzzyLookup(options.searchValue, commands, (c) => c.name);
        } else {
            // we have to sort the commands by category to avoid navigation issues with the arrows
            if (namespaceConfig.categories) {
                let commandsSorted = [];
                this.categoryKeys = namespaceConfig.categories;
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

        this.state.commands = markRaw(
            commands.slice(0, 100).map((command) => ({
                ...command,
                keyId: this.keyId++,
                splitName: splitCommandName(command.name, options.searchValue),
            }))
        );
        this.selectCommand(this.state.commands.length ? 0 : -1);
        this.mouseSelectionActive = false;
        this.state.emptyMessage = (
            namespaceConfig.emptyMessage || DEFAULT_EMPTY_MESSAGE
        ).toString();
    }

    selectCommand(index) {
        if (index === -1 || index >= this.state.commands.length) {
            this.state.selectedCommand = null;
            return;
        }
        this.state.selectedCommand = markRaw(this.state.commands[index]);
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

        const command = this.listboxRef.el.querySelector(`#o_command_${nextIndex}`);
        scrollTo(command, { scrollable: this.listboxRef.el });
    }

    onCommandClicked(event, index) {
        event.preventDefault(); // Prevent redirect for commands with href
        this.selectCommand(index);
        const ctrlKey = isMacOS() ? event.metaKey : event.ctrlKey;
        this.executeSelectedCommand(ctrlKey);
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
            this.props.close();
        }
    }

    async executeSelectedCommand(ctrlKey) {
        await this.searchValuePromise;
        const selectedCommand = this.state.selectedCommand;
        if (selectedCommand) {
            if (!ctrlKey) {
                this.executeCommand(selectedCommand);
            } else if (selectedCommand.href) {
                window.open(selectedCommand.href, "_blank");
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

    async search(searchValue) {
        this.state.searchValue = searchValue;
        await this.setCommands(this.state.namespace, {
            searchValue,
            activeElement: this.activeElement,
            sessionId: this._sessionId,
        });
        if (this.inputRef.el) {
            this.inputRef.el.focus();
        }
    }

    debounceSearch(value) {
        const { namespace, searchValue } = this.processSearchValue(value);
        if (namespace !== "default" && this.state.namespace !== namespace) {
            this.switchNamespace(namespace);
        }
        this.inputRef.el.value = searchValue;
        this.searchValuePromise = this.lastDebounceSearch(searchValue).catch(() => {
            this.searchValuePromise = null;
        });
    }

    onSearchInput(ev) {
        this.debounceSearch(ev.target.value);
    }

    onKeyDown(ev) {
        if (ev.key.toLowerCase() === "backspace" && !ev.target.value.length && !ev.repeat) {
            this.switchNamespace("default");
            this.searchValuePromise = this.lastDebounceSearch("").catch(() => {
                this.searchValuePromise = null;
            });
        }
    }

    /**
     * Close the palette on outside click.
     */
    onWindowMouseDown(ev) {
        if (!this.root.el.contains(ev.target)) {
            this.props.close();
        }
    }

    switchNamespace(namespace) {
        if (this.lastDebounceSearch) {
            this.lastDebounceSearch.cancel();
        }
        const namespaceConfig = this.configByNamespace[namespace] || {};
        this.lastDebounceSearch = debounce(
            (value) => this.search(value),
            namespaceConfig.debounceDelay || 0
        );
        this.state.namespace = namespace;
        this.state.placeholder = namespaceConfig.placeholder || DEFAULT_PLACEHOLDER.toString();
    }

    processSearchValue(searchValue) {
        let namespace = "default";
        if (searchValue.length && this.providersByNamespace[searchValue[0]]) {
            namespace = searchValue[0];
            searchValue = searchValue.slice(1);
        }
        return { namespace, searchValue };
    }

    get isMacOS() {
        return isMacOS();
    }
    get isMobileOS() {
        return isMobileOS();
    }
}
CommandPalette.lastSessionId = 0;
CommandPalette.template = "web.CommandPalette";
CommandPalette.components = { Dialog };
