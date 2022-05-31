/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one, many } from '@mail/model/model_field';

registerModel({
    name: 'Emoji',
    identifyingFields: ['unicode'],
    fields: {
        description: attr({
            readonly: true,
            required: true,
        }),
        emojiRegistry: one('EmojiRegistry', {
            inverse: 'allEmojis',
            readonly: true,
            required: true,
        }),
        emojiViews: many('EmojiView', {
            inverse: 'emoji',
            readonly: true,
            isCausal: true,
        }),
        sources: attr({
            readonly: true,
            required: true,
        }),
        unicode: attr({
            readonly: true,
            required: true,
        }),
    },
});
