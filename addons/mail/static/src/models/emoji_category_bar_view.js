/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'EmojiCategoryBarView',
    fields: {
        activeByUserCategoryView: one('EmojiCategoryView', {
            inverse: 'emojiCategoryBarViewOwnerAsActiveByUser',
        }),
        activeCategoryView: one('EmojiCategoryView', {
            compute() {
                if (this.emojiPickerViewOwner.emojiSearchBarView.currentSearch !== "") {
                    return clear();
                }
                if (this.activeByUserCategoryView) {
                    return this.activeByUserCategoryView;
                }
                if (this.defaultActiveCategoryView) {
                    return this.defaultActiveCategoryView;
                }
                return clear();
            },
            inverse: 'emojiCategoryBarViewOwnerAsActive',
        }),
        defaultActiveCategoryView: one('EmojiCategoryView', {
            compute() {
                if (!this.messaging.emojiRegistry) {
                    return clear();
                }
                if (this.messaging.emojiRegistry.allCategories.length === 0) {
                    return clear();
                }
                return {
                    emojiCategory: this.messaging.emojiRegistry.allCategories[0],
                    emojiCategoryBarViewOwner: this,
                };
            },
        }),
        emojiCategoryViews: many('EmojiCategoryView', {
            compute() {
                return this.messaging.emojiRegistry.allCategories.map(emojiCategory => ({ emojiCategory }));
            },
            inverse: 'emojiCategoryBarViewOwner',
            isCausal: true,
        }),
        emojiPickerViewOwner: one('EmojiPickerView', {
            identifying: true,
            inverse: 'emojiCategoryBarView',
        }),
    },
});
