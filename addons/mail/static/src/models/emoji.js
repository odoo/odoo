/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { insertAndReplace } from '@mail/model/model_field_command';

registerModel({
    name: 'Emoji',
    identifyingFields: ['unicode'],
    fields: {
        description: attr({
            readonly: true,
            required: true,
        }),
        emojiRegistry: one('EmojiRegistry', {
            default: insertAndReplace(),
            inverse: 'allEmojis',
            readonly: true,
            required: true,
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
