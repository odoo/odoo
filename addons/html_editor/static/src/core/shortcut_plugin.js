import { isMacOS } from "@web/core/browser/feature_detection";
import { Plugin } from "../plugin";
import { closestBlock } from "@html_editor/utils/blocks";
import { fillEmpty } from "@html_editor/utils/dom";
import { leftLeafOnlyNotBlockPath } from "@html_editor/utils/dom_state";

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

    resources = {
        input_handlers: this.onInput.bind(this),
    };

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
        super.destroy();
        this.removeEditorCommandPalette();
    }

    addShortcut(hotkey, action) {
        this.services.hotkey.add(hotkey, action, {
            area: () => this.editable,
            bypassEditableProtection: true,
            allowRepeat: true,
            rawModifiers: isMacOS(),
        });
    }

    onInput(ev) {
        if (ev.data !== " ") {
            return;
        }
        const selection = this.dependencies.selection.getEditableSelection();
        if (!(this.checkPredicates("are_shorthands_available", selection.anchorNode) ?? true)) {
            return;
        }
        const blockEl = closestBlock(selection.anchorNode);
        const leftDOMPath = leftLeafOnlyNotBlockPath(selection.anchorNode);
        let spaceOffset = selection.anchorOffset;
        let leftLeaf = leftDOMPath.next().value;
        while (leftLeaf) {
            // Calculate spaceOffset by adding lengths of previous text nodes
            // to correctly find offset position for selection within inline
            // elements. e.g. <p>ab<strong>cd []e</strong></p>
            spaceOffset += leftLeaf.length;
            leftLeaf = leftDOMPath.next().value;
        }
        const precedingText = blockEl.textContent.substring(0, spaceOffset - 1);
        const matchedShortcut = this.getResource("shorthands").find(({ pattern }) =>
            pattern.test(precedingText)
        );
        if (matchedShortcut) {
            const command = this.dependencies.userCommand.getCommand(matchedShortcut.commandId);
            if (command) {
                this.dependencies.selection.setSelection({
                    anchorNode: blockEl.firstChild,
                    anchorOffset: 0,
                    focusNode: selection.focusNode,
                    focusOffset: selection.focusOffset,
                });
                this.dependencies.selection.extractContent(
                    this.dependencies.selection.getEditableSelection()
                );
                fillEmpty(blockEl);
                command.run(matchedShortcut.commandParams);
            }
        }
    }
}
