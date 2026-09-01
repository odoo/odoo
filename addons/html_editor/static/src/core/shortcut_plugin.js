/** @odoo-module native */
import { closestBlock } from "@html_editor/utils/blocks";
import { leftLeafOnlyNotBlockPath } from "@html_editor/utils/dom_state";

import { isValidTargetForDomListener, Plugin } from "../plugin.js";

/**
 * @typedef {Object} Shortcut
 * @property {string} hotkey
 * @property {string} commandId
 * @property {Object} [commandParams]
 * @property {boolean} [global]
 * @typedef {Shortcut[]} shortcuts
 */

/**
 * @typedef {{
 * pattern: RegExp;
 * commandId: string;
 * commandParams?: object;
 * }[]} shorthands
 */

export class ShortCutPlugin extends Plugin {
    static id = "shortcut";
    static dependencies = ["userCommand", "selection", "delete", "split"];

    /** @type {import("plugins").EditorResources} */
    resources = {
        input_handlers: this.onInput.bind(this),
    };

    setup() {
        const hotkeyService = this.services.hotkey;
        if (!hotkeyService) {
            throw new Error("ShorcutPlugin needs hotkey service to properly work");
        }

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
            },
        );
        if (document !== this.document) {
            this._cleanups.push(
                hotkeyService.registerIframe({ contentWindow: this.window }),
            );
        }
        for (const shortcut of this.getResource("shortcuts")) {
            const command = this.dependencies.userCommand.getCommand(
                shortcut.commandId,
            );
            this.addShortcut(
                shortcut.hotkey,
                () => {
                    command.run(shortcut.commandParams);
                },
                {
                    isAvailable: command.isAvailable,
                    global: !!shortcut.global,
                },
            );
        }
        this.shorthands = this.getResource("shorthands");
    }

    destroy() {
        super.destroy();
        this.removeEditorCommandPalette();
    }

    addShortcut(hotkey, action, { isAvailable, global }) {
        this._cleanups.push(
            this.services.hotkey.add(hotkey, action, {
                area: () => this.editable,
                bypassEditableProtection: true,
                allowRepeat: true,
                isAvailable: (target) =>
                    (!isAvailable ||
                        isAvailable(
                            this.dependencies.selection.getEditableSelection(),
                        )) &&
                    (global || isValidTargetForDomListener(target)),
            }),
        );
    }

    onInput(ev) {
        if (ev.data !== " ") {
            return;
        }
        const selection = this.dependencies.selection.getEditableSelection();
        if (!(
            this.checkPredicates("are_shorthands_available", selection.anchorNode) ??
            true
        )) {
            return;
        }
        let blockEl = closestBlock(selection.anchorNode);
        const leftDOMPath = leftLeafOnlyNotBlockPath(selection.anchorNode);
        let spaceOffset = selection.anchorOffset;
        // Offset of the beginning of the line the caret is on, within the
        // block: everything after the closest line break to its left.
        let lineBreak;
        let lineOffset = 0;
        let leftLeaf = leftDOMPath.next().value;
        while (leftLeaf) {
            spaceOffset += leftLeaf.length || 0;
            if (lineBreak) {
                lineOffset += leftLeaf.length || 0;
            } else if (leftLeaf.nodeName === "BR") {
                lineBreak = leftLeaf;
            }
            leftLeaf = leftDOMPath.next().value;
        }
        const precedingText = blockEl.textContent.substring(
            lineOffset,
            spaceOffset - 1,
        );
        const matchedShortcut = this.shorthands.find(({ pattern }) =>
            pattern.test(precedingText),
        );
        if (matchedShortcut) {
            const command = this.dependencies.userCommand.getCommand(
                matchedShortcut.commandId,
            );
            if (command && command.isAvailable(selection)) {
                if (lineBreak) {
                    // Isolate the line so that the command applies to it alone
                    // and `blockEl.firstChild` below is the start of the line.
                    this.dependencies.split.splitBlockSegments();
                    blockEl = closestBlock(selection.anchorNode);
                }
                this.dependencies.selection.setSelection({
                    anchorNode: blockEl.firstChild,
                    anchorOffset: 0,
                    focusNode: selection.focusNode,
                    focusOffset: selection.focusOffset,
                });
                this.dependencies.delete.deleteSelection();
                command.run(matchedShortcut.commandParams);
            }
        }
    }
}
