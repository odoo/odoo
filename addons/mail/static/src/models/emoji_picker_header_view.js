/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'EmojiPickerHeaderView',
    fields: {
        actionListView: one('EmojiPickerHeaderActionListView', {
            default: {},
            isCausal: true,
            inverse: 'owner',
        }),
        emojiCategoryBarView: one('EmojiCategoryBarView', {
            default: {},
            inverse: 'emojiPickerHeaderViewOwner',
            readonly: true,
            required: true,
        }),
        emojiPickerViewOwner: one('EmojiPickerView', {
            identifying: true,
            inverse: 'headerView',
        }),
    },
});
