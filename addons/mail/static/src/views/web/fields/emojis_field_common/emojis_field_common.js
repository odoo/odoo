import { useRef } from "@web/owl2/utils";
import { useEmojiPicker } from "@web/core/emoji_picker/emoji_picker";


/*
 * Common code for EmojisTextField and EmojisCharField
 */
export const EmojisFieldCommon = (T) =>
    class EmojisFieldCommon extends T {
        /**
         * Create an emoji textfield view to enable opening an emoji popover
         */
        _setupOverride() {
            this.emojiPicker = useEmojiPicker(
                useRef("emojisButton"),
                {
                    onSelect: (codepoints) => {
                        const el = this.targetEditElement();
                        if (!el) {
                            return;
                        }
                        const originalContent = el.value;
                        const start = el.selectionStart;
                        const end = el.selectionEnd;
                        const left = originalContent.slice(0, start);
                        const right = originalContent.slice(end, originalContent.length);
                        el.value = left + codepoints + right;
                        // trigger onInput from input_field hook to set field as dirty
                        el.dispatchEvent(new InputEvent("input"));
                        // keydown serves to both commit the changes in input_field and trigger onchange for some fields
                        el.dispatchEvent(new KeyboardEvent("keydown"));
                        el.focus();
                        const newCursorPos = start + codepoints.length;
                        el.setSelectionRange(newCursorPos, newCursorPos);
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
