import { Plugin } from "@html_editor/plugin";
import { EmojiPicker } from "@web/core/emoji_picker/emoji_picker";
import { _t } from "@web/core/l10n/translation";

export class EmojiPlugin extends Plugin {
    static name = "emoji";
    static dependencies = ["overlay", "dom", "selection"];
    static shared = ["showEmojiPicker"];
    resources = {
        powerboxItems: [
            {
                category: "widget",
                name: _t("Emoji"),
                description: _t("Add an emoji"),
                fontawesome: "fa-smile-o",
                action: () => {
                    this.showEmojiPicker();
                },
            },
        ],
    };

    setup() {
        this.overlay = this.shared.createOverlay(EmojiPicker, {
            hasAutofocus: true,
            className: "popover",
        });
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
                    this.shared.focusEditable();
                },
                onSelect: (str) => {
                    if (onSelect) {
                        onSelect(str);
                        return;
                    }
                    this.shared.domInsert(str);
                    this.dispatch("ADD_STEP");
                },
            },
            target,
        });
    }
}
