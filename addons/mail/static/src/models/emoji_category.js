/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { replace } from '@mail/model/model_field_command';
import { categoryTitleByCategoryName } from '@mail/models_data/emoji_data';

registerModel({
    name: 'EmojiCategory',
    identifyingFields: ['categoryName'],
    recordMethods: {
        /**
         * @returns {string}
         */
        _computeCategoryTitle() {
            if (categoryTitleByCategoryName.has(this.categoryName)) {
                return categoryTitleByCategoryName.get(this.categoryName);
            }
            return this.categoryName;
        },
        /**
         * @returns {FieldCommand}
         */
        _computeEmojiRegistry() {
            return replace(this.messaging.emojiRegistry);
        },
    },
    fields: {
        allEmojis: many('Emoji', {
            inverse: 'emojiCategories',
        }),
        categoryName: attr({
            readonly: true,
            required: true,
        }),
        categoryTitle: attr({
            compute: '_computeCategoryTitle',
        }),
        emojiCategoryViews: many('EmojiCategoryView', {
            inverse: 'emojiCategory',
            isCausal: true,
        }),
        emojiRegistry: one("EmojiRegistry", {
            compute: '_computeEmojiRegistry',
            inverse: "allCategories",
            required: true,
        }),
    },
});
