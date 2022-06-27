/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { insertAndReplace } from '@mail/model/model_field_command';

registerModel({
    name: 'EmojiPickerView',
    identifyingFields: ['popoverViewOwner'],
    fields: {
        emojiCategoryBarView: one('EmojiCategoryBarView', {
            default: insertAndReplace(),
            inverse: 'emojiPickerViewOwner',
            readonly: true,
            required: true,
            isCausal: true,
        }),
        emojiGridView: one('EmojiGridView', {
            default: insertAndReplace(),
            inverse: 'emojiPickerViewOwner',
            readonly: true,
            required: true,
            isCausal: true,
        }),
        popoverViewOwner: one('PopoverView', {
            inverse: 'emojiPickerView',
            readonly: true,
            required: true,
        }),
    },
});
