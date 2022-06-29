/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'EmojiView',
    identifyingFields: ['emoji', 'emojiPickerView'],
    fields: {
        emoji: one('Emoji', {
            inverse: 'emojiViews',
            readonly: true,
            required: true,
        }),
        emojiPickerView: one('EmojiPickerView', {
            inverse: 'emojiViews',
            readonly: true,
            required: true,
        }),
    }
});
