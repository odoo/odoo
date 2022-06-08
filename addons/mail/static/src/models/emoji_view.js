/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'EmojiView',
    identifyingFields: ['emoji', 'emojiList'],
    fields: {
        emoji: one('Emoji', {
            inverse: 'emojiViews',
            readonly: true,
            required: true,
        }),
        emojiList: one('EmojiList', {
            inverse: 'emojiViews',
            readonly: true,
            required: true,
        }),
    },
});
