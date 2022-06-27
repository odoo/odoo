/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many, one } from '@mail/model/model_field';
import { clear, insertAndReplace, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'EmojiGridView',
    identifyingFields: ['emojiPickerViewOwner'],
    recordMethods: {
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeEmojiViews() {
            if (!this.emojiPickerViewOwner.emojiCategoryBarView.activeCategoryView) {
                return clear();
            }
            return insertAndReplace(
                this.emojiPickerViewOwner.emojiCategoryBarView.activeCategoryView.emojiCategory.allEmojis.map(emoji => {
                    return { emoji: replace(emoji) };
                })
            );
        },
    },
    fields: {
        emojiPickerViewOwner: one('EmojiPickerView', {
            inverse: 'emojiGridView',
            readonly: true,
            required: true,
        }),
        emojiViews: many('EmojiView', {
            compute: '_computeEmojiViews',
            inverse: 'emojiGridView',
            readonly: true,
            isCausal: true,
        }),
    },
});
