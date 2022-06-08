/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { replace } from '@mail/model/model_field_command';

registerModel({
    name: 'EmojiCategory',
    identifyingFields: ['categoryName'],
    recordMethods: {
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeEmojiRegistry() {
            return replace(this.messaging.emojiRegistry);
        },
    },
    fields: {
        allEmojis: many('Emoji', {
            inverse: 'emojiCategories',
        }),
        categoryName: attr({
            readonly: true,
            required: true,
        }),
        emojiCategoryViews: many('EmojiCategoryView', {
            inverse: 'emojiCategory',
            readonly: true,
            isCausal: true,
        }),
        emojiRegistry: one('EmojiRegistry', {
            compute: '_computeEmojiRegistry',
            inverse: 'allCategories',
            required: true,
        }),
    },
});
