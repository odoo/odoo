/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'EmojiGridView',
    recordMethods: {
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeEmojiViews() {
            if (!this.emojiPickerViewOwner.emojiCategoryBarView.activeCategoryView) {
                return clear();
            }
            if (this.emojiPickerViewOwner.emojiSearchBar.currentSearch !== "") {
                const filtered_emojis = this.emojiPickerViewOwner.emojiCategoryBarView.activeCategoryView.emojiCategory.allEmojis.filter(this._filterEmoji);
                return filtered_emojis.map(emoji => ({ emoji }));
            }
            return this.emojiPickerViewOwner.emojiCategoryBarView.activeCategoryView.emojiCategory.allEmojis.map(emoji => ({ emoji }));
        },
        /**
         * @private
         * @returns {boolean}
         * Filters amoji according to the current search terms.
         */
        _filterEmoji(emoji) {
            return (emoji._isStringInEmojiKeywords(this.emojiPickerViewOwner.emojiSearchBar.currentSearch));
        },
    },
    fields: {
        emojiPickerViewOwner: one('EmojiPickerView', {
            identifying: true,
            inverse: 'emojiGridView',
        }),
        emojiViews: many('EmojiView', {
            compute: '_computeEmojiViews',
            inverse: 'emojiGridView',
            readonly: true,
            isCausal: true,
        }),
    },
});
