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
            return this.emojiPickerViewOwner.emojiCategoryBarView.activeCategoryView.emojiCategory.allEmojis.map(emoji => ({ emoji }));
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
            isCausal: true,
        }),
    },
});
