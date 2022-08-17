/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';

registerModel({
    name: 'EmojiGridView',
    recordMethods: {
        _computeEmojiSubgridViews() {
            return this.emojiPickerViewOwner.emojiCategoryBarView.emojiCategoryViews.map(emojiCategoryView => ({ emojiCategoryView }));
        }
    },
    fields: {
        component: attr(),
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
