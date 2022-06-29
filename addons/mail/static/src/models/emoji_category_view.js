/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'EmojiCategoryView',
    identifyingFields: ['emojiCategory', 'emojiPickerView'],
    fields: {
        emojiCategory: one('EmojiCategory', {
            inverse: 'emojiCategoryViews',
            readonly: true,
            required: true,
        }),
        emojiPickerView: one('EmojiPickerView', {
            inverse: 'emojiCategoryViews',
            readonly: true,
            required: true,
        }),
    }
});
