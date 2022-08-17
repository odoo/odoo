/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { insertAndReplace, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'EmojiGridView',
    identifyingFields: ['emojiPickerViewOwner'],
    recordMethods: {
        _computeEmojiSubgridViews() {
            return insertAndReplace(
                this.emojiPickerViewOwner.emojiCategoryBarView.emojiCategoryViews.map(emojiCategoryView => {
                    return ({emojiCategoryView: replace(emojiCategoryView)});
                })
            );
        }
    },
    fields: {
        component: attr(),
        emojiPickerViewOwner: one('EmojiPickerView', {
            inverse: 'emojiGridView',
            readonly: true,
            required: true,
        }),
        emojiSubgridViews: many('EmojiSubgridView', {
            compute: "_computeEmojiSubgridViews",
            inverse: 'emojiGridViewOwner',
            readonly: true,
            isCausal: true,
        }),
        thresholdLineForStickyRef: attr(),
    },
});
