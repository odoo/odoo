/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'EmojiKeyword',
    identifyingFields: ['emoji'],
    fields: {
        emoji: one('Emoji', {
            required: true,
            inverse: 'emojiKeywords',
            readonly: true,
        }),
        keyword: attr({
            readonly: true,
            required: true,
        }),
    },
});
