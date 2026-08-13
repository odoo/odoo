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
