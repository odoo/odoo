import { Plugin } from "@html_editor/plugin";
import { reactive } from "@odoo/owl";
import { EmojiPicker, loadEmoji, loader } from "@web/core/emoji_picker/emoji_picker";
import { _t } from "@web/core/l10n/translation";
import { debounce } from "@web/core/utils/timing";
import { fuzzyLookup } from "@web/core/utils/search";
import { isContentEditable, isTextNode } from "@html_editor/utils/dom_info";
import { SuggestionList } from "@html_editor/components/suggestion/suggestion_list";

/**
 * @typedef { Object } EmojiShared
 * @property { EmojiPlugin['showEmojiPicker'] } showEmojiPicker
 */

export class EmojiPlugin extends Plugin {
    static id = "emoji";
    static dependencies = ["history", "overlay", "dom", "selection", "delete"];
    static shared = ["showEmojiPicker"];
    /** @type {import("plugins").EditorResources} */
    resources = {
        delete_backward_overrides: this.handleDeleteBackward.bind(this),
        input_handlers: this.onInput.bind(this),
        delete_handlers: () => this.updateEmojiList(),
        post_undo_handlers: () => this.updateEmojiList(),
        post_redo_handlers: () => this.updateEmojiList(),
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
        this.emojiListOverlay = this.dependencies.overlay.createOverlay(SuggestionList, {
            className: "popover",
        });
        this.match = undefined;
        const { emojis } = await loadEmoji();
        this.allEmojis = emojis;
        this.emojiListState = reactive({ list: [] });
        this.addDomListener(this.document, "keydown", this.onKeyDown);
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

    onInput(ev) {
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
            this.emojiListOverlay.close();
            this.dependencies.dom.insert(emoji.codepoints);
            this.dependencies.history.addStep();
            this.match = match;
            return;
        }
        this.match = undefined;
        if (ev.data === ":") {
            this.emojiListOverlay.close();
            const selection = this.dependencies.selection.getEditableSelection();
            this.offset = start - 1;
            this.shouldUpdateEmojiList = true;
            this.searchNode = selection.startContainer;
        } else if (this.isSearching(selection)) {
            this.updateEmojiList();
        } else {
            this.emojiListOverlay.close();
            this.shouldUpdateEmojiList = false;
        }
    }

    onKeyDown(ev) {
        if (ev.key === "Escape") {
            this.emojiListOverlay.close();
            this.shouldUpdateEmojiList = false;
        }
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

    updateEmojiList = debounce(this._updateEmojiList, 100);
    _updateEmojiList() {
        if (!this.shouldUpdateEmojiList) {
            return;
        }

        const selection = this.dependencies.selection.getEditableSelection();
        const searchTerm = this.searchNode.nodeValue.slice(this.offset, selection.endOffset) || "";
        const emojis = fuzzyLookup(searchTerm, this.allEmojis, (e) => [
            e.name,
            ...e.shortcodes,
            ...e.keywords,
        ]).slice(0, 8);
        this.emojiListState.list = emojis.map((e) => ({
            value: e.codepoints,
            label: e.shortcodes[0],
        }));
        if (searchTerm.length > 2 && emojis.length) {
            this.emojiListOverlay.open({
                props: {
                    state: this.emojiListState,
                    onSelect: ({ value }) => {
                        const selection = this.document.getSelection();
                        selection.extend(this.searchNode, this.offset);
                        this.dependencies.delete.deleteSelection();
                        this.dependencies.dom.insert(value);
                        this.dependencies.history.addStep();
                        this.emojiListOverlay.close();
                    },
                    overlay: this.emojiListOverlay,
                },
            });
        } else {
            this.emojiListOverlay.close();
        }
    }

    isSearching(selection) {
        return (
            selection.endContainer === this.searchNode &&
            this.searchNode.nodeValue &&
            this.searchNode.nodeValue[this.offset] === ":" &&
            selection.endOffset > this.offset
        );
    }
}
