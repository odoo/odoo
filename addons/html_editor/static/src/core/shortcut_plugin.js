import { Plugin } from "../plugin";

/**
 * @typedef {Object} Shortcut
 * @property {string} hotkey
 * @property {string} commandId
 * @property {Object} [commandParams]
 *
 * Example:
 *
 *     resources = {
 *         user_commands: [
 *             { id: "myCommands", run: myCommandFunction },
 *         ],
 *         shortcuts: [
 *             { hotkey: "control+shift+q", commandId: "myCommands" },
 *         ],
 *     }
 */

export class ShortCutPlugin extends Plugin {
    static id = "shortcut";
    static dependencies = ["userCommand"];

    setup() {
        const hotkeyService = this.services.hotkey;
        if (!hotkeyService) {
            throw new Error("ShorcutPlugin needs hotkey service to properly work");
        }
        if (document !== this.document) {
            hotkeyService.registerIframe({ contentWindow: this.document.defaultView });
        }
        for (const shortcut of this.getResource("shortcuts")) {
            const command = this.dependencies.userCommand.getCommand(shortcut.commandId);
            this.addShortcut(shortcut.hotkey, () => {
                command.run(shortcut.commandParams);
            });
        }
    }

    addShortcut(hotkey, action) {
        this.services.hotkey.add(hotkey, action, {
            area: () => this.editable,
            bypassEditableProtection: true,
            allowRepeat: true,
        });
    }
}
