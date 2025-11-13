import { Plugin, isValidTargetForDomListener } from "../plugin";
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
                {
                    isAvailable: command.isAvailable,
                    global: !!shortcut.global,
                }
            );
        }
    }

    addShortcut(hotkey, action, { isAvailable, global }) {
        this._cleanups.push(
            this.services.hotkey.add(hotkey, action, {
                area: () => this.editable,
                bypassEditableProtection: true,
                allowRepeat: true,
                isAvailable: (target) =>
                    (!isAvailable ||
                        isAvailable(this.dependencies.selection.getEditableSelection())) &&
                    (global || isValidTargetForDomListener(target)),
            })
        );
    }

    onInput(ev) {
        if (ev.data !== " ") {
            return;
        }
        const selection = this.dependencies.selection.getEditableSelection();
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
