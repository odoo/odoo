/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'EmojiView',
    identifyingFields: ['emojiGridView', 'emoji'],
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        onClick(ev) {
            if (this.emojiGridView.emojiPickerViewOwner.popoverViewOwner.messageActionListOwnerAsReaction) {
                this.emojiGridView.emojiPickerViewOwner.popoverViewOwner.messageActionListOwnerAsReaction.onClickReaction(ev);
                return;
            }
            if (this.emojiGridView.emojiPickerViewOwner.popoverViewOwner.composerViewOwnerAsEmoji) {
                this.emojiGridView.emojiPickerViewOwner.popoverViewOwner.composerViewOwnerAsEmoji.onClickEmoji(ev);
                return;
            }
        },
        /**
         * @param {MouseEvent} ev
         */
        onMouseenter(ev) {
            this.update({ isHovered: true });
        },
        /**
         * @param {MouseEvent} ev
         */
        onMouseleave(ev) {
            this.update({ isHovered: false });
        },
    },
    fields: {
        emoji: one('Emoji', {
            inverse: 'emojiViews',
            readonly: true,
            required: true,
        }),
        emojiGridView: one('EmojiGridView', {
            inverse: 'emojiViews',
            readonly: true,
            required: true,
        }),
        isHovered: attr({
            default: false,
        }),
    }
});
