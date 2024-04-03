/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many, one } from '@mail/model/model_field';

registerModel({
    name: 'EmojiOrEmojiInCategory',
    identifyingMode: 'xor',
    fields: {
        emoji: one('Emoji', {
            identifying: true,
            inverse: 'emojiOrEmojiInCategory',
        }),
        emojiInCategory: one('EmojiInCategory', {
            identifying: true,
            inverse: 'emojiOrEmojiInCategory',
        }),
        emojiGridItemViews: many('EmojiGridItemView', {
            inverse: 'emojiOrEmojiInCategory',
        }),
    },
});
