/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many, one } from '@mail/model/model_field';
import { clear, insertAndReplace } from '@mail/model/model_field_command';

registerModel({
    name: 'EmojiPickerView',
    identifyingFields: ['popoverViewOwner'],
    recordMethods: {
        _computeActiveCategory() {
            if (this.visibleSubgridViews.length === 0) {
                return clear();
            }
            return (this.visibleSubgridViews[0]);
        },
        /*_sortVisibleEmojiSubgridViews() {
            return [['smaller-first', 'emojiCategoryView.emojiCategory.sortId']];
        },*/
    },
    fields: {
        emojiCategories: many('EmojiCategoryView', {
        }),
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
        emojiSearchBar: one('EmojiSearchBar', {
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
        visibleSubgridViews: many('EmojiSubgridView', {
            inverse: 'emojiPickerViewAsVisible',
            //sort: '_sortVisibleEmojiSubgridViews',
            isCausal: true,
        }),
        activeCategory: one('EmojiCategory', {
            compute: '_computeActiveCategory',
        }),
    },
});
