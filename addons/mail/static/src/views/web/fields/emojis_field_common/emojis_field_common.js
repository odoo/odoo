import { useEmojiPicker } from "@web/core/emoji_picker/emoji_picker";
import { signal } from "@odoo/owl";

/*
 * Common code for EmojisTextField and EmojisCharField
 */
export const EmojisFieldCommon = (T) =>
    class EmojisFieldCommon extends T {
        /**
         * Create an emoji textfield view to enable opening an emoji popover
         */
        _setupOverride() {
            this.emojisButton = signal();
            this.emojiPicker = useEmojiPicker(
                this.emojisButton,
                {
                    onSelect: (codepoints) => {
                        const originalContent = this.targetEditElement().value;
                        const start = this.targetEditElement().selectionStart;
                        const end = this.targetEditElement().selectionEnd;
                        const left = originalContent.slice(0, start);
                        const right = originalContent.slice(end, originalContent.length);
                        this.targetEditElement().value = left + codepoints + right;
                        // trigger onInput from input_field hook to set field as dirty
                        this.targetEditElement().dispatchEvent(new InputEvent("input"));
                        // keydown serves to both commit the changes in input_field and trigger onchange for some fields
                        this.targetEditElement().dispatchEvent(new KeyboardEvent("keydown"));
                        this.targetEditElement().focus();
                        const newCursorPos = start + codepoints.length;
                        this.targetEditElement().setSelectionRange(newCursorPos, newCursorPos);
                        if (this._emojiAdded) {
                            this._emojiAdded();
                        }
                    },
                },
                {
                    position: "bottom",
                }
            );
        }
    };
