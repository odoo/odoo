/** @odoo-module **/

import { clear, one, registerModel } from '@mail/model';

registerModel({
    name: 'EmojiView',
    template: 'mail.EmojiView',
    templateGetter: 'emojiView',
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        onClick(ev) {
            if (!this.emojiGridItemViewOwner.emojiGridRowViewOwner) {
                return;
            }
            if (this.emojiPickerViewOwner.popoverViewOwner.messageActionViewOwnerAsReaction) {
                this.emojiPickerViewOwner.popoverViewOwner.messageActionViewOwnerAsReaction.onClickReaction(ev);
                return;
            }
            if (this.emojiPickerViewOwner.popoverViewOwner.composerViewOwnerAsEmoji) {
                this.emojiPickerViewOwner.popoverViewOwner.composerViewOwnerAsEmoji.onClickEmoji(ev);
                return;
            }
        },
        /**
         * @param {MouseEvent} ev
         */
        onMouseenter(ev) {
            if (!this.exists()) {
                return;
            }
            this.update({ emojiGridViewAsHovered: this.emojiGridItemViewOwner.emojiGridRowViewOwner.emojiGridViewOwner });
        },
        /**
         * @param {MouseEvent} ev
         */
        onMouseleave(ev) {
            if (!this.exists()) {
                return;
            }
            this.update({ emojiGridViewAsHovered: clear() });
        },
    },
    fields: {
        emoji: one('Emoji', { identifying: true, inverse: 'emojiViews' }),
        emojiGridItemViewOwner: one('EmojiGridItemView', { identifying: true, inverse: 'emojiView' }),
        emojiGridViewAsHovered: one('EmojiGridView', { inverse: 'hoveredEmojiView' }),
        emojiPickerViewOwner: one('EmojiPickerView', {
            compute() {
                return this.emojiGridItemViewOwner.emojiGridRowViewOwner.emojiGridViewOwner.emojiPickerViewOwner;
            }
        })
    },
});
