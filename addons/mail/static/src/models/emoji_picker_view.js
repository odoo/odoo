/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'EmojiPickerView',
    identifyingFields: ['popoverViewOwner'],
    recordMethods: {
        _computeActiveCategory() {
            if (this.visibleSubgridViews.length === 0) {
                return clear();
            }
            return (this.visibleSubgridViews[0].emojiCategoryView.emojiCategory);
        },
        _sortVisibleEmojiSubgridViews() {
            return [['smaller-first', 'emojiCategoryView.emojiCategory.sortId']];
        },
    },
    fields: {
        emojiCategories: many('EmojiCategoryView', {
        }),
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
        emojiSearchBar: one('EmojiSearchBar', {
            default: {},
            inverse: 'emojiPickerView',
            readonly: true,
            isCausal: true,
        }),
        popoverViewOwner: one('PopoverView', {
            identifying: true,
            inverse: 'emojiPickerView',
        }),
        visibleSubgridViews: many('EmojiSubgridView', {
            inverse: 'emojiPickerViewAsVisible',
            sort: '_sortVisibleEmojiSubgridViews',
            isCausal: true,
        }),
        activeCategory: one('EmojiCategory', {
            compute: '_computeActiveCategory',
        }),
    },
});
