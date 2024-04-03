/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many, one } from '@mail/model/model_field';

registerModel({
    name: 'EmojiInCategory',
    fields: {
        category: one('EmojiCategory', {
            identifying: true,
            inverse: 'allEmojiInCategoryOfCurrent',
        }),
        emoji: one('Emoji', {
            identifying: true,
            inverse: 'allEmojiInCategoryOfCurrent',
        }),
        emojiOrEmojiInCategory: many('EmojiOrEmojiInCategory', {
            inverse: 'emojiInCategory',
        }),
    },
});
