/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'EmojiView',
    identifyingFields: ['emoji', 'emojiListView'],
    fields: {
        emoji: one('Emoji', {
            inverse: 'emojiViews',
            readonly: true,
            required: true,
        }),
        emojiListView: one('EmojiListView', {
            inverse: 'emojiViews',
            readonly: true,
            required: true,
        }),
    }
});
