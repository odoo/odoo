import { Plugin } from "../plugin";

/**
 * @typedef {Object} Shortcut
 * @property {string} hotkey
 * @property {string} commandId
 * @property {Object} [commandParams]
 * @property {boolean} [global]
 *
 * @typedef {Shortcut[]} shortcuts
 *
 * Example:
 *
 *     resources = {
 *         // See UserCommand
 *         user_commands: [
 *             { id: "myCommands", run: myCommandFunction },
 *         ],
 *         // See Shortcut
 *         shortcuts: [
 *             { hotkey: "control+shift+q", commandId: "myCommands" },
 *         ],
 *     }
 */

/**
 * @typedef {{
 *     pattern: RegExp;
 *     commandId: string;
 *     commandParams?: object;
 * }[]} shorthands
 */

export class ShortCutPlugin extends Plugin {
    static id = "shortcut";
    static dependencies = ["userCommand", "selection"];

    setup() {
        const hotkeyService = this.services.hotkey;
        if (!hotkeyService) {
            throw new Error("ShorcutPlugin needs hotkey service to properly work");
        }
        if (document !== this.document) {
            hotkeyService.registerIframe({ contentWindow: this.window });
        }
        for (const shortcut of this.getResource("shortcuts")) {
            const command = this.dependencies.userCommand.getCommand(shortcut.commandId);
            this.addShortcut(
                shortcut.hotkey,
                () => {
                    command.run(shortcut.commandParams);
                },
                { isAvailable: command.isAvailable }
            );
        }
    }

    addShortcut(hotkey, action, { isAvailable }) {
        this.services.hotkey.add(hotkey, action, {
            area: () => this.editable,
            bypassEditableProtection: true,
            allowRepeat: true,
            isAvailable: () =>
                isAvailable
                    ? isAvailable(this.dependencies.selection.getEditableSelection())
                    : true,
        });
    }
}
