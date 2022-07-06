/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'EmojiCategoryBarView',
    recordMethods: {
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeActiveCategoryView() {
            if (this.activeByUserCategoryView) {
                return this.activeByUserCategoryView;
            }
            if (this.defaultActiveCategoryView) {
                return this.defaultActiveCategoryView;
            }
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeDefaultActiveCategoryView() {
            return {
                emojiCategory: { name: "all" },
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
