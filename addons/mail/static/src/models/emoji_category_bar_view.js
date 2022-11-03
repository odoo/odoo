/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'EmojiCategoryBarView',
    template: 'mail.EmojiCategoryBarView',
    fields: {
        emojiCategoryViews: many('EmojiCategoryView', { inverse: 'emojiCategoryBarViewOwner',
            compute() {
                if (!this.emojiPickerViewOwner) {
                    return clear();
                }
                return this.emojiPickerViewOwner.categories.map(category => ({ viewCategory: category }));
            },
        }),
        emojiPickerViewOwner: one('EmojiPickerView', { identifying: true, inverse: 'emojiCategoryBarView' }),
    },
});
