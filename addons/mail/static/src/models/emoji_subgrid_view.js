/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';

registerModel({
    name: 'EmojiSubgridView',
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
                return filtered_emojis.map(emoji => ({ emoji: emoji }));
            }
            return this.emojiCategoryView.emojiCategory.allEmojis.map(emoji => ({ emoji: emoji }));
        },
        /**
         * @private
         * @returns {boolean}
         * Filters emoji according to the current search terms.
         */
        _filterEmoji(emoji) {
            return (emoji._isStringInEmojiKeywords(this.emojiGridViewOwner.emojiPickerViewOwner.emojiSearchBar.currentSearch));
        },
    },
    fields: {
        component: attr(),
        emojiCategoryView: one('EmojiCategoryView', {
            identifying: true,
            inverse: "emojiSubgridView",
        }),
        emojiGridViewOwner: one('EmojiGridView', {
            inverse: 'emojiSubgridViews',
            readonly: true,
            required: true,
        }),
        emojiViews: many('EmojiView', {
            compute: '_computeEmojiViews',
            inverse: 'emojiSubgridViewOwner',
            readonly: true,
            isCausal: true,
        }),
        name: attr({
            compute: '_computeCategoryName',
        }),
        emojiPickerViewAsVisible: one('EmojiPickerView', {
            inverse: 'visibleSubgridViews',
        }),
    }
});
