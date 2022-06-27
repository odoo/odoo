/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { insertAndReplace } from '@mail/model/model_field_command';

registerModel({
    name: 'EmojiPickerView',
    identifyingFields: ['popoverViewOwner'],
    fields: {
        emojiCategoryBar: one('EmojiCategoryBar', {
            default: insertAndReplace(),
            inverse: 'emojiPickerView',
            readonly: true,
            isCausal: true,
        }),
        emojiList: one('EmojiList', {
            default: insertAndReplace(),
            inverse: 'emojiPickerView',
            readonly: true,
            isCausal: true,
        }),
        popoverViewOwner: one('PopoverView', {
            inverse: 'emojiPickerView',
            readonly: true,
            required: true,
        }),
    },
});
