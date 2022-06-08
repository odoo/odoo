/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { insertAndReplace } from '@mail/model/model_field_command';

registerModel({
    name: 'EmojiPickerView',
    identifyingFields: ['popoverViewOwner'],
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        onClickEmoji(ev) {
            if (this.popoverViewOwner.messageActionListOwnerAsReaction) {
                this.popoverViewOwner.messageActionListOwnerAsReaction.onClickReaction(ev);
            } else if (this.popoverViewOwner.composerViewOwnerAsEmoji) {
                this.popoverViewOwner.composerViewOwnerAsEmoji.onClickEmoji(ev);
            }
        },
    },
    fields: {
        emojiCategoryBar: one('EmojiCategoryBar', {
            default: insertAndReplace(),
            inverse: 'emojiPickerView',
            readonly: true,
            isCausal: true,
        }),
        emojiList: one('EmojiList', {
            default: insertAndReplace(),
            inverse: 'emojiPickerView',
            readonly: true,
            isCausal: true,
        }),
        popoverViewOwner: one('PopoverView', {
            inverse: 'emojiPickerView',
            readonly: true,
            required: true,
        }),
    },
});
