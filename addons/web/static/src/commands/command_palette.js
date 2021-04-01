/** @odoo-module **/
import { useAutofocus } from "../core/hooks";
import { useHotkey } from "../hotkey/hotkey_hook";
import { scrollTo } from "../utils/scrolling";
const { Component, hooks } = owl;
const { onPatched, useState } = hooks;

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
      categoryName === "default" && !odoo.commandCategoryRegistry.contains(cmd.category);
    return inCurrentCategory || fallbackCategory;
  };
}

export class CommandPalette extends Component {
  setup() {
    /**
     * @type Command[]
     */
    this.initialCommands = [];
    for (const [key, _] of odoo.commandCategoryRegistry.getEntries()) {
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
    onPatched(() => {
      const index = this.state.commands.indexOf(this.state.selectedCommand);
      const listbox = this.el.querySelector(".o_command_palette_listbox");
      const command = listbox.querySelector(`#o_command_${index}`);
      scrollTo(command, listbox);
    });
    useHotkey(
      "Enter",
      () => {
        this.executeSelectedCommand();
      },
      { altIsOptional: true }
    );
    useHotkey(
      "ArrowUp",
      () => {
        this.mouseSelectionActive = false;
        const index = this.state.commands.indexOf(this.state.selectedCommand);
        if (index > 0) {
          this.selectCommand(index - 1);
        }
      },
      { altIsOptional: true, allowRepeat: true }
    );
    useHotkey(
      "ArrowDown",
      () => {
        this.mouseSelectionActive = false;
        const index = this.state.commands.indexOf(this.state.selectedCommand);
        if (index < this.state.commands.length - 1) {
          this.selectCommand(index + 1);
        }
      },
      { altIsOptional: true, allowRepeat: true }
    );
  }

  get categories() {
    const categories = [];
    for (const [key, value] of odoo.commandCategoryRegistry.getEntries()) {
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

  selectCommand(index) {
    if (index === -1 || index >= this.state.commands.length) {
      this.state.selectedCommand = null;
      return;
    }
    this.state.selectedCommand = this.state.commands[index];
  }

  onCommandClicked(index) {
    this.selectCommand(index);
    this.executeSelectedCommand();
  }

  executeSelectedCommand() {
    if (this.state.selectedCommand) {
      this.trigger("dialog-closed");
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
