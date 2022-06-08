/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'EmojiCategoryView',
    identifyingFields: ['emojiCategory', 'emojiListView'],
    fields: {
        emojiCategory: one('EmojiCategory', {
            inverse: 'emojiCategoryViews',
            readonly: true,
            required: true,
        }),
        emojiListView: one('EmojiListView', {
            inverse: 'emojiCategoryViews',
            readonly: true,
            required: true,
        }),
    }
});
