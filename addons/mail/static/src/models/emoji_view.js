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
            if (this.emojiSubgridViewOwner.emojiGridViewOwner.emojiPickerViewOwner.popoverViewOwner.messageActionListOwnerAsReaction) {
                this.emojiSubgridViewOwner.emojiGridViewOwner.emojiPickerViewOwner.popoverViewOwner.messageActionListOwnerAsReaction.onClickReaction(ev);
                return;
            }
            if (this.emojiSubgridViewOwner.emojiGridViewOwner.emojiPickerViewOwner.popoverViewOwner.composerViewOwnerAsEmoji) {
                this.emojiSubgridViewOwner.emojiGridViewOwner.emojiPickerViewOwner.popoverViewOwner.composerViewOwnerAsEmoji.onClickEmoji(ev);
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
            this.update({ isHovered: true });
        },
        /**
         * @param {MouseEvent} ev
         */
        onMouseleave(ev) {
            if (!this.exists()) {
                return;
            }
            this.update({ isHovered: false });
        },
    },
    fields: {
        emoji: one('Emoji', {
            identifying: true,
            inverse: 'emojiViews',
        }),
        emojiSubgridViewOwner: one('EmojiSubgridView', {
            identifying: true,
            inverse: 'emojiViews',
        }),
        isHovered: attr({
            default: false,
        }),
    }
});
