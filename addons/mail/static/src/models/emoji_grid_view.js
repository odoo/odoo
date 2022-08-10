/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many, one } from '@mail/model/model_field';

registerModel({
    name: 'EmojiGridView',
    recordMethods: {
        _computeEmojiSubgridViews() {
            return this.emojiPickerViewOwner.emojiCategoryBarView.emojiCategoryViews.map(emojiCategoryView => ({ emojiCategoryView }));
        }
    },
    fields: {
        emojiPickerViewOwner: one('EmojiPickerView', {
            identifying: true,
            inverse: 'emojiGridView',
        }),
        emojiSubgridViews: many('EmojiSubgridView', {
            compute: "_computeEmojiSubgridViews",
            inverse: 'emojiGridViewOwner',
            readonly: true,
            isCausal: true,
        }),
    },
});
