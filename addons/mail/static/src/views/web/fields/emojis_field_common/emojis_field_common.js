import { useEmojiPicker } from "@web/core/emoji_picker/emoji_picker";

import { useRef } from "@odoo/owl";

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
                        const originalContent = this.targetEditElement.el.value;
                        const start = this.targetEditElement.el.selectionStart;
                        const end = this.targetEditElement.el.selectionEnd;
                        const left = originalContent.slice(0, start);
                        const right = originalContent.slice(end, originalContent.length);
                        this.targetEditElement.el.value = left + codepoints + right;
                        // trigger onInput from input_field hook to set field as dirty
                        this.targetEditElement.el.dispatchEvent(new InputEvent("input"));
                        // keydown serves to both commit the changes in input_field and trigger onchange for some fields
                        this.targetEditElement.el.dispatchEvent(new KeyboardEvent("keydown"));
                        this.targetEditElement.el.focus();
                        const newCursorPos = start + codepoints.length;
                        this.targetEditElement.el.setSelectionRange(newCursorPos, newCursorPos);
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
