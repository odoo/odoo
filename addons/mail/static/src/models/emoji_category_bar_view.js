/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many, one } from '@mail/model/model_field';

registerModel({
    name: 'EmojiCategoryBarView',
    recordMethods: {
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeActiveCategoryView() {
            if (!this.activeByUserCategoryView) {
                return this.defaultActiveCategoryView;
            }
            return this.activeByUserCategoryView;
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeDefaultActiveCategoryView() {
            return {
                emojiCategory: { categoryName: "all" },
                emojiCategoryBarViewOwner: this,
            };
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeEmojiCategoryViews() {
            return this.messaging.emojiRegistry.allCategories.map(emojiCategory => ({ emojiCategory }));
        },
    },
    fields: {
        activeByUserCategoryView: one('EmojiCategoryView', {
            inverse: 'emojiCategoryBarViewOwnerAsActiveByUser',
        }),
        activeCategoryView: one('EmojiCategoryView', {
            compute: '_computeActiveCategoryView',
            inverse: 'emojiCategoryBarViewOwnerAsActive',
            required: true,
        }),
        defaultActiveCategoryView: one('EmojiCategoryView', {
            compute: '_computeDefaultActiveCategoryView',
        }),
        emojiCategoryViews: many('EmojiCategoryView', {
            compute: '_computeEmojiCategoryViews',
            inverse: 'emojiCategoryBarViewOwner',
            isCausal: true,
        }),
        emojiPickerViewOwner: one('EmojiPickerView', {
            identifying: true,
            inverse: 'emojiCategoryBarView',
        }),
    },
});
