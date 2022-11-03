/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'EmojiPickerView',
    template: 'mail.EmojiPickerView',
    componentSetup() {
        useComponentToModel({ fieldName: 'component' });
    },
    lifecycleHooks: {
        _created() {
            if (this.messaging.emojiRegistry.isLoaded || this.messaging.emojiRegistry.isLoading) {
                return;
            }
            this.messaging.emojiRegistry.loadEmojiData();
        },
    },
    fields: {
        actionListView: one('EmojiPickerHeaderActionListView', { default: {}, isCausal: true, inverse: 'owner' }),
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
        categories: many('EmojiPickerView.Category', { inverse: 'emojiPickerViewOwner',
            compute() {
                return this.messaging.emojiRegistry.allCategories.map(category => ({ category }));
            },
        }),
        defaultActiveCategory: one('EmojiPickerView.Category', {
            compute() {
                if (this.categories.length === 0) {
                    return clear();
                }
                return this.categories[0];
            },
        }),
        emojiCategoryBarView: one('EmojiCategoryBarView', { default: {}, inverse: 'emojiPickerViewOwner', readonly: true, required: true }),
        emojiGridView: one('EmojiGridView', { default: {}, inverse: 'emojiPickerViewOwner', readonly: true, required: true }),
        emojiSearchBarView: one('EmojiSearchBarView', { default: {}, inverse: 'emojiPickerView', readonly: true }),
        popoverViewOwner: one('PopoverView', { identifying: true, inverse: 'emojiPickerView' }),
        component: attr(),
    },
});
