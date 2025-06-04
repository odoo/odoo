import { closestElement } from "@html_editor/utils/dom_traversal";
import { Plugin } from "../plugin";

/**
 * @typedef { import("./selection_plugin").EditorSelection } EditorSelection
 */

/**
 * @typedef { Object } UserCommand
 * @property { string } id
 * @property { Function } run
 * @property { String } [title]
 * @property { String } [description]
 * @property { string } [icon]
 * @property { (selection: EditorSelection) => boolean  } [isAvailable]
 */

/**
 * @typedef { Object } UserCommandShared
 * @property { UserCommandPlugin['getCommand'] } getCommand
 */

export class UserCommandPlugin extends Plugin {
    static id = "userCommand";
    static shared = ["getCommand"];

    setup() {
        this.commands = {};
        for (const command of this.getResource("user_commands")) {
            if (command.id in this.commands) {
                throw new Error(`Duplicate user command id: ${command.id}`);
            }
            if (!command.plainTextCompatible) {
                const isAvailable = command.isAvailable;
                command.isAvailable = isAvailable
                    ? (selection) => isAvailable(selection) && isSelectionInHtmlContent(selection)
                    : isSelectionInHtmlContent;
            }
            this.commands[command.id] = command;
        }
        Object.freeze(this.commands);
    }

    /**
     * @param {string} commandId
     * @returns {UserCommand}
     * @throws {Error} if the command ID is unknown.
     */
    getCommand(commandId) {
        const command = this.commands[commandId];
        if (!command) {
            throw new Error(`Unknown user command id: ${commandId}`);
        }
        return command;
    }
}

export function isSelectionInHtmlContent(selection) {
    return !closestElement(
        selection.focusNode,
        // TODO: which selector should be used ?:
        // '[data-oe-model]:not([data-oe-field="arch"]):not([data-oe-type="html"]),[data-oe-translation-id]'
        // '[data-oe-model]:not([data-oe-field="arch"],[data-oe-field="arch_db"]):not([data-oe-type="html"])'
        '[data-oe-model]:not([data-oe-type="html"]):not([data-oe-field="arch"]):not([data-oe-translation-source-sha])'
    );
}
