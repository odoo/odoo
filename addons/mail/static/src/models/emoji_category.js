/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many } from '@mail/model/model_field';

registerModel({
    name: 'EmojiCategory',
    fields: {
        allEmojis: many('Emoji', {
            inverse: 'emojiCategories',
        }),
        categoryName: attr({
            identifying: true,
        }),
        emojiCategoryViews: many('EmojiCategoryView', {
            inverse: 'emojiCategory',
            isCausal: true,
        }),
    },
});
