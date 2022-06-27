/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many } from '@mail/model/model_field';

registerModel({
    name: 'EmojiCategory',
    identifyingFields: ['categoryName'],
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
            isCausal: true,
        }),
    },
});
