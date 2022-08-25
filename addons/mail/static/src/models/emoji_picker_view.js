/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'EmojiPickerView',
    fields: {
        emojiCategoryBarView: one('EmojiCategoryBarView', {
            default: {},
            inverse: 'emojiPickerViewOwner',
            readonly: true,
            required: true,
            isCausal: true,
        }),
        emojiGridView: one('EmojiGridView', {
            default: {},
            inverse: 'emojiPickerViewOwner',
            readonly: true,
            required: true,
            isCausal: true,
        }),
        popoverViewOwner: one('PopoverView', {
            identifying: true,
            inverse: 'emojiPickerView',
        }),
    },
});
