/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'EmojiEmoticon',
    identifyingFields: ['emoji'],
    fields: {
        emoji: one('Emoji', {
            required: true,
            inverse: 'emojiEmoticons',
            readonly: true,
        }),
        emoticon: attr({
            readonly: true,
            required: true,
        }),
    },
});
