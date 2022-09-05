/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'EmojiPickerView',
    fields: {
        component: attr(),
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
        emojiCategoryRowIndexes: attr({
            default: new Map(),
        }),
        emojiSearchBarView: one('EmojiSearchBarView', {
            default: {},
            inverse: 'emojiPickerView',
            readonly: true,
            isCausal: true,
        }),
        popoverViewOwner: one('PopoverView', {
            identifying: true,
            inverse: 'emojiPickerView',
        }),
    },
});
