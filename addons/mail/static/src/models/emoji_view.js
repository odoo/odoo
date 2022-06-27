/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'EmojiView',
    identifyingFields: ['emoji', 'emojiList'],
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        onClick(ev) {
            if (this.emojiList.emojiPickerView.popoverViewOwner.messageActionListOwnerAsReaction) {
                this.emojiList.emojiPickerView.popoverViewOwner.messageActionListOwnerAsReaction.onClickReaction(ev);
            } else if (this.emojiList.emojiPickerView.popoverViewOwner.composerViewOwnerAsEmoji) {
                this.emojiList.emojiPickerView.popoverViewOwner.composerViewOwnerAsEmoji.onClickEmoji(ev);
            }
        },
    },
    fields: {
        emoji: one('Emoji', {
            inverse: 'emojiViews',
            readonly: true,
            required: true,
        }),
        emojiList: one('EmojiList', {
            inverse: 'emojiViews',
            readonly: true,
            required: true,
        }),
    }
});
