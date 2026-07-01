import { signal } from "@odoo/owl";
import { useEmojiPicker } from "@web/core/emoji_picker/emoji_picker";

/*
 * Common code for EmojisTextField and EmojisCharField
 */
export const EmojisFieldCommon = (T) =>
    class EmojisFieldCommon extends T {
        emojisButtonRef = signal(null);

        /**
         * Create an emoji textfield view to enable opening an emoji popover
         */
        _setupOverride() {
            this.emojiPicker = useEmojiPicker(
                this.emojisButtonRef,
                {
                    onSelect: (codepoints) => {
                        const targetEl = this.targetEditElement();
                        const originalContent = targetEl.value;
                        const start = targetEl.selectionStart;
                        const end = targetEl.selectionEnd;
                        const left = originalContent.slice(0, start);
                        const right = originalContent.slice(end, originalContent.length);
                        targetEl.value = left + codepoints + right;
                        // trigger onInput from input_field hook to set field as dirty
                        targetEl.dispatchEvent(new InputEvent("input"));
                        // keydown serves to both commit the changes in input_field and trigger onchange for some fields
                        targetEl.dispatchEvent(new KeyboardEvent("keydown"));
                        targetEl.focus();
                        const newCursorPos = start + codepoints.length;
                        targetEl.setSelectionRange(newCursorPos, newCursorPos);
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
