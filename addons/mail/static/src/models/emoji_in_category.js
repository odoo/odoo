/** @odoo-module **/

import { many, one, registerModel } from '@mail/model';

registerModel({
    name: 'EmojiInCategory',
    fields: {
        category: one('EmojiCategory', { identifying: true, inverse: 'allEmojiInCategoryOfCurrent' }),
        emoji: one('Emoji', { identifying: true, inverse: 'allEmojiInCategoryOfCurrent' }),
        emojiOrEmojiInCategory: many('EmojiOrEmojiInCategory', { inverse: 'emojiInCategory' }),
    },
});
