/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'EmojiSkin',
    identifyingFields: ['emoji'],
    fields: {
        emoji: one('Emoji', {
            required: true,
            inverse: 'emojiSkins',
            readonly: true,
        }),
        unified: attr({
            readonly: true,
            required: true,
        }),
        native: attr({
            readonly: true,
            required: true,
        }),
    },
});
