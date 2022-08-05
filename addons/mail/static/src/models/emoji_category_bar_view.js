/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many, one } from '@mail/model/model_field';

registerModel({
    name: 'EmojiCategoryBarView',
    fields: {
        emojiCategoryViews: many('EmojiCategoryView', {
            compute() {
                return this.emojiPickerViewOwner.categories.map(category => ({ viewCategory: category }));
            },
            inverse: 'emojiCategoryBarViewOwner',
            isCausal: true,
        }),
        emojiPickerViewOwner: one('EmojiPickerView', {
            identifying: true,
            inverse: 'emojiCategoryBarView',
        }),
    },
});
