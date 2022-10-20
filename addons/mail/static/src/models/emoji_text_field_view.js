/** @odoo-module **/

import { attr, clear, one, Model} from '@mail/model';


Model({
    name: 'EmojiTextFieldView',
    recordMethods: {
        /**
         * On selecting an emoji from the list
         *
         * @param {MouseEvent} ev
         */
        onClickEmoji(ev) {
            const emojiCharacter = ev.currentTarget.dataset.codepoints;

            const [start, end] = this.textSelection;
            const originalContent = this.textInputRef.el.value;
            const left = originalContent.slice(0, start);
            const right = originalContent.slice(end, originalContent.length);
            this.textInputRef.el.value = left + emojiCharacter + right;

            // trigger onInput from input_field hook to set field as dirty
            this.textInputRef.el.dispatchEvent(new InputEvent('input'));
            // keydown serves to both commit the changes in input_field and trigger onchange for some fields
            this.textInputRef.el.dispatchEvent(new KeyboardEvent("keydown"));
            this.textInputRef.el.focus();
            const newCursorPos = this.textSelection[0] + emojiCharacter.length;
            this.textInputRef.el.setSelectionRange(newCursorPos, newCursorPos);
            if (this.inputModifiedCallback) {
                this.inputModifiedCallback();
            }

            this.toggleEmojiPopover();
        },
        toggleEmojiPopover() {
           this.update({
               emojisPopoverView: this.emojisPopoverView ? clear() : {},
               textSelection: [this.textInputRef.el.selectionStart, this.textInputRef.el.selectionEnd],
           });
        },
    },
    fields: {
        buttonEmojisRef: attr(),
        textSelection: attr(),
        emojisPopoverView: one('PopoverView', {
            inverse: 'emojiTextFieldViewOwner',
        }),
        textInputRef: attr({
            identifying: true,
        }),
        // callbacks
        inputModifiedCallback: attr(),
    },
});
