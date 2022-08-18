/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'EmojiView',
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        onClick(ev) {
            if (this.emojiGridView.emojiPickerViewOwner.popoverViewOwner.messageActionViewOwnerAsReaction) {
                this.emojiGridView.emojiPickerViewOwner.popoverViewOwner.messageActionViewOwnerAsReaction.onClickReaction(ev);
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
            identifying: true,
            inverse: 'emojiViews',
        }),
        emojiGridView: one('EmojiGridView', {
            identifying: true,
            inverse: 'emojiViews',
        }),
        isHovered: attr({
            default: false,
        }),
    }
});
