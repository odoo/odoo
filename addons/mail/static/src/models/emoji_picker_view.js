/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'EmojiPickerView',
    fields: {
        activeCategoryByGridViewScroll: one('EmojiPickerView.Category'),
        activeCategory: one('EmojiPickerView.Category', {
            compute() {
                if (this.emojiSearchBarView.currentSearch !== "") {
                    return clear();
                }
                if (this.activeCategoryByGridViewScroll) {
                    return this.activeCategoryByGridViewScroll;
                }
                if (this.defaultActiveCategory) {
                    return this.defaultActiveCategory;
                }
                return clear();
            },
            inverse: 'emojiPickerViewAsActive',
        }),
        categories: many('EmojiPickerView.Category', {
            compute() {
                return this.messaging.emojiRegistry.allCategories.map(category => ({ category }));
            },
            inverse: 'emojiPickerViewOwner',
        }),
        defaultActiveCategory: one('EmojiPickerView.Category', {
            compute() {
                if (this.categories.length === 0) {
                    return clear();
                }
                return this.categories[0];
            },
        }),
        emojiCategoryBarView: one('EmojiCategoryBarView', {
            default: {},
            inverse: 'emojiPickerViewOwner',
            readonly: true,
            required: true,
        }),
        emojiGridView: one('EmojiGridView', {
            default: {},
            inverse: 'emojiPickerViewOwner',
            readonly: true,
            required: true,
        }),
        emojiSearchBarView: one('EmojiSearchBarView', {
            default: {},
            inverse: 'emojiPickerView',
            readonly: true,
        }),
        popoverViewOwner: one('PopoverView', {
            identifying: true,
            inverse: 'emojiPickerView',
        }),
        component: attr(),
    },
});
