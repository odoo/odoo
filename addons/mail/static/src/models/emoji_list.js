/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many, one } from '@mail/model/model_field';
import { insertAndReplace, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'EmojiList',
    identifyingFields: ['emojiPickerView'],
    recordMethods: {
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeEmojiViews() {
            return insertAndReplace(
                this.messaging.emojiRegistry.currentCategory.allEmojis.map(emoji => {
                    return { emoji: replace(emoji) };
                })
            );
        },
    },
    fields: {
        emojiViews: many('EmojiView', {
            compute: '_computeEmojiViews',
            inverse: 'emojiList',
            readonly: true,
            isCausal: true,
        }),
        emojiPickerView: one('EmojiPickerView', {
            inverse: 'emojiList',
            readonly: true,
            required: true,
        }),
    },
});
