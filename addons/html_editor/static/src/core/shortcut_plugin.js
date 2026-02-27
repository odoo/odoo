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
    static dependencies = ["userCommand", "selection"];

    setup() {
        const hotkeyService = this.services.hotkey;
        if (!hotkeyService) {
            throw new Error("ShorcutPlugin needs hotkey service to properly work");
        }

        // We override the command palette shortcut to open a palette with an
        // onClose callback to focus the editor and keep the selection without
        // scrolling. We also pass the editable as the area option for this
        // hotkey override, so it only applies when calling the command palette
        // from the editor.
        this.removeEditorCommandPalette = this.services.hotkey.add(
            "control+k",
            () => {
                this.services.command.openMainPalette({}, () => {
                    this.dependencies.selection.focusEditable();
                });
            },
            {
                bypassEditableProtection: true,
                global: true,
                area: () => this.editable,
            }
        );
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

    destroy() {
        this.removeEditorCommandPalette();
    }

    addShortcut(hotkey, action) {
        this.services.hotkey.add(hotkey, action, {
            area: () => this.editable,
            bypassEditableProtection: true,
            allowRepeat: true,
        });
    }
}
