/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { insertAndReplace, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'EmojiSubgridView',
    identifyingFields: ['emojiCategoryView'],
    recordMethods: {
        _computeCategoryName() {
            return this.emojiCategoryView.emojiCategory.name;
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeEmojiViews() {
            if (this.emojiGridViewOwner.emojiPickerViewOwner.emojiSearchBar.currentSearch !== "") {
                const filtered_emojis = this.emojiCategoryView.emojiCategory.allEmojis.filter(this._filterEmoji);
                return insertAndReplace(
                    filtered_emojis.map(emoji => {
                        return { emoji: replace(emoji) };
                    })
                );
            }
            return insertAndReplace(
                this.emojiCategoryView.emojiCategory.allEmojis.map(emoji => {
                    return { emoji: replace(emoji) };
                })
            );
        },
        /**
         * @private
         * @returns {boolean}
         * Filters amoji according to the current search terms.
         */
        _filterEmoji(emoji) {
            return (emoji._isStringInEmojiKeywords(this.emojiGridViewOwner.emojiPickerViewOwner.emojiSearchBar.currentSearch));
        },
    },
    fields: {
        emojiCategoryView: one('EmojiCategoryView', {
            required: true,
            readonly: true,
            inverse: "emojiSubgridView",
        }),
        emojiGridViewOwner: one('EmojiGridView', {
            inverse: 'emojiSubgridViews',
            readonly: true,
            required: true,
        }),
        emojiViews: many('EmojiView', {
            compute: '_computeEmojiViews',
            inverse: 'emojiSubgridView',
            readonly: true,
            isCausal: true,
        }),
        categoryNameRef: attr(),
        name: attr({
            compute: '_computeCategoryName',
        }),
    }
});
