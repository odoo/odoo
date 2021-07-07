/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useAutofocus } from "../../core/autofocus_hook";
import { isMacOS } from "../../core/browser/feature_detection";
import { useHotkey } from "../../core/hotkey_hook";
import { scrollTo } from "../../core/utils/scrolling";

const { Component, hooks } = owl;
const { useState } = hooks;

const commandCategoryRegistry = registry.category("command_categories");
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

export class CommandPalette extends Component {
    setup() {
        /**
         * @type Command[]
         */
        this.initialCommands = [];
        for (const [key, _] of commandCategoryRegistry.getEntries()) {
            const commands = this.props.commands.filter(commandsWithinCategory(key));
            this.initialCommands = this.initialCommands.concat(commands);
        }

        /**
         * @type {{commands:Command[], selectedCommand: Command}}
         */
        this.state = useState({
            commands: this.initialCommands,
            selectedCommand: this.initialCommands[0],
        });

        useAutofocus();

        this.mouseSelectionActive = false;
        useHotkey("Enter", () => this.executeSelectedCommand());
        useHotkey("ArrowUp", () => this.selectCommandAndScrollTo("PREV"), { allowRepeat: true });
        useHotkey("ArrowDown", () => this.selectCommandAndScrollTo("NEXT"), { allowRepeat: true });

        for (const command of this.initialCommands) {
            if (command.hotkey) {
                useHotkey(command.hotkey, () => {
                    command.action();
                    this.props.closeMe();
                });
            }
        }
    }

    get categories() {
        const categories = [];
        for (const [key, value] of commandCategoryRegistry.getEntries()) {
            const commands = this.state.commands.filter(commandsWithinCategory(key));
            if (commands.length) {
                categories.push({
                    ...value,
                    commands,
                });
            }
        }
        return categories;
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
        scrollTo(command, listbox);
    }

    onCommandClicked(index) {
        this.selectCommand(index);
        this.executeSelectedCommand();
    }

    executeSelectedCommand() {
        if (this.state.selectedCommand) {
            this.props.closeMe();
            this.state.selectedCommand.action();
        }
    }

    onCommandMouseEnter(index) {
        if (this.mouseSelectionActive) {
            this.selectCommand(index);
        } else {
            this.mouseSelectionActive = true;
        }
    }

    onSearchInput(ev) {
        const searchValue = ev.target.value;
        const newCommands = [];
        for (const command of this.initialCommands) {
            if (fuzzy.test(searchValue, command.name)) {
                newCommands.push(command);
            }
        }
        this.state.commands = newCommands;
        this.selectCommand(this.state.commands.length ? 0 : -1);
    }
}
CommandPalette.template = "web.CommandPalette";
