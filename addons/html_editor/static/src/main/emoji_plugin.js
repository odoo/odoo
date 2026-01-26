import { Plugin } from "@html_editor/plugin";
import { EmojiPicker, loadEmoji, loader } from "@web/core/emoji_picker/emoji_picker";
import { _t } from "@web/core/l10n/translation";
import { isContentEditable, isTextNode } from "@html_editor/utils/dom_info";

/**
 * @typedef { Object } EmojiShared
 * @property { EmojiPlugin['showEmojiPicker'] } showEmojiPicker
 */

export class EmojiPlugin extends Plugin {
    static id = "emoji";
    static dependencies = ["history", "overlay", "dom", "selection"];
    static shared = ["showEmojiPicker"];
    /** @type {import("plugins").EditorResources} */
    resources = {
        delete_backward_overrides: this.handleDeleteBackward.bind(this),
        input_handlers: this.detect.bind(this),
        user_commands: [
            {
                id: "addEmoji",
                title: _t("Emoji"),
                description: _t("Add an emoji"),
                icon: "fa-smile-o",
                run: this.showEmojiPicker.bind(this),
            },
        ],
        powerbox_items: [
            {
                categoryId: "widget",
                commandId: "addEmoji",
            },
        ],
    };

    async setup() {
        await super.setup();
        this.overlay = this.dependencies.overlay.createOverlay(EmojiPicker, {
            hasAutofocus: true,
            className: "popover",
        });
        this.match = undefined;
        await loadEmoji();
    }

    get emojiDict() {
        return loader.loaded?.emojiSourceToEmoji ?? new Map();
    }

    handleDeleteBackward() {
        if (this.match) {
            this.dependencies.history.undo();
            this.match = undefined;
            return true;
        }
    }

    detect() {
        const selection = this.dependencies.selection.getEditableSelection();
        if (
            !isTextNode(selection.startContainer) ||
            !isContentEditable(selection.startContainer) ||
            !selection.isCollapsed
        ) {
            this.match = undefined;
            return;
        }
        const start = selection.startOffset;
        const text = selection.anchorNode.textContent;

        for (let candidatePosition = start - 1; candidatePosition >= 0; candidatePosition--) {
            let match = null;
            for (const key of this.emojiDict.keys()) {
                if (text.substring(candidatePosition) === key) {
                    match = key;
                }
            }
            if (!match) {
                continue;
            }
            // Ensure the character before is a space or start of text
            const charBefore = text[candidatePosition - 1];
            if (charBefore && !/\s/.test(charBefore)) {
                continue;
            }
            // Replace the matched text with the emoji
            const emoji = this.emojiDict.get(match);
            this.dependencies.selection.setSelection({
                anchorNode: selection.anchorNode,
                anchorOffset: candidatePosition,
                focusNode: selection.focusNode,
                focusOffset: start,
            });
            this.dependencies.dom.insert(emoji.codepoints);
            this.dependencies.history.addStep();
            this.match = match;
            return;
        }
        this.match = undefined;
    }

    /**
     * @param {Object} options
     * @param {HTMLElement} options.target - The target element to position the overlay.
     * @param {Function} [options.onSelect] - The callback function to handle the selection of an emoji.
     * If not provided, the emoji will be inserted into the editor and a step will be trigerred.
     */
    showEmojiPicker({ target, onSelect } = {}) {
        this.overlay.open({
            props: {
                close: () => {
                    this.overlay.close();
                    this.dependencies.selection.focusEditable();
                },
                onSelect: (str) => {
                    if (onSelect) {
                        onSelect(str);
                        return;
                    }
                    this.dependencies.dom.insert(str);
                    this.dependencies.history.addStep();
                },
            },
            target,
        });
    }
}
