import { Plugin, isValidTargetForDomListener } from "../plugin";
import { closestBlock } from "@html_editor/utils/blocks";
import { fillEmpty } from "@html_editor/utils/dom";
import { leftLeafOnlyNotBlockPath } from "@html_editor/utils/dom_state";
import { omit } from "@web/core/utils/objects";
import { escapeRegExp } from "@web/core/utils/strings";

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
 *     literals: string[];
 *     commandId: string;
 *     commandParams?: object;
 * }[]} shorthands
 */

export class ShortCutPlugin extends Plugin {
    static id = "shortcut";
    static dependencies = ["userCommand", "selection", "split", "dom", "history"];

    /** @type {import("plugins").EditorResources} */
    resources = {
        input_handlers: this.onInput.bind(this),
        user_commands: [
            {
                id: "replaceSymbol",
                run: ({ symbol }) => this.replaceSymbol(symbol),
            },
        ],
        shorthands: [
            {
                literals: ["->"],
                commandId: "replaceSymbol",
                commandParams: { symbol: "\u2192" }, //→
                inline: true,
            },
            {
                literals: ["<-"],
                commandId: "replaceSymbol",
                commandParams: { symbol: "\u2190" }, //←
                inline: true,
            },
            {
                literals: ["=>"],
                commandId: "replaceSymbol",
                commandParams: { symbol: "\u2B95" }, //⮕
                inline: true,
            },
        ],
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
        this.shorthands = this.getResource("shorthands").map((shorthand) => {
            const pattern = `${shorthand.inline ? "" : "^"}(${shorthand.literals
                .map(escapeRegExp)
                .join("|")})$`;
            return {
                ...omit(shorthand, "literals"),
                pattern: new RegExp(pattern),
            };
        });
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

    replaceSymbol(symbol) {
        this.dependencies.dom.insert(symbol + "\u00A0");
        this.dependencies.history.addStep();
    }

    onInput(ev) {
        if (ev.data !== " ") {
            return;
        }
        const selection = this.dependencies.selection.getEditableSelection();
        let blockEl = closestBlock(selection.anchorNode);
        const leftDOMPath = leftLeafOnlyNotBlockPath(selection.anchorNode);
        let spaceOffset = selection.anchorOffset;
        let lineBreak;
        let lineOffset = 0;
        let leftLeaf = leftDOMPath.next().value;
        while (leftLeaf) {
            // Calculate spaceOffset by adding lengths of previous text nodes
            // to correctly find offset position for selection within inline
            // elements. e.g. <p>ab<strong>cd []e</strong></p>
            spaceOffset += leftLeaf.length || 0;
            // Similarly, calculate lineOffset to find the beginning of the line
            // by adding lengths of previous nodes from the moment a line break
            // is found.
            if (lineBreak) {
                lineOffset += leftLeaf.length || 0;
            } else if (leftLeaf.nodeName === "BR") {
                lineBreak = leftLeaf;
            }
            leftLeaf = leftDOMPath.next().value;
        }
        const precedingText = blockEl.textContent.substring(lineOffset, spaceOffset - 1);
        const matchedShortcut = this.shorthands.find(({ pattern }) =>
            pattern.test(precedingText.trimStart())
        );
        if (matchedShortcut) {
            const command = this.dependencies.userCommand.getCommand(matchedShortcut.commandId);
            if (command) {
                if (lineBreak) {
                    this.dependencies.split.splitBlockSegments();
                    blockEl = closestBlock(selection.anchorNode);
                }
                // Set selection to the matched string with space
                let offset =
                    matchedShortcut.pattern.exec(precedingText.trimStart())?.[0].length + 1;
                while (offset > 0) {
                    this.dependencies.selection.modifySelection("extend", "backward", "character");
                    offset--;
                }
                this.dependencies.selection.extractContent(
                    this.dependencies.selection.getEditableSelection()
                );
                fillEmpty(blockEl);
                command.run(matchedShortcut.commandParams);
            }
        }
    }
}
