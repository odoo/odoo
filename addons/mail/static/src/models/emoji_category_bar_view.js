/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many, one } from '@mail/model/model_field';
import { insertAndReplace, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'EmojiCategoryBarView',
    identifyingFields: ['emojiPickerViewOwner'],
    recordMethods: {
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeEmojiCategoryViews() {
            return insertAndReplace(
                this.messaging.emojiRegistry.allCategories.map(emojiCategory => {
                    return { emojiCategory: replace(emojiCategory) };
                })
            );
        },
    },
    fields: {
        emojiCategoryViews: many('EmojiCategoryView', {
            compute: '_computeEmojiCategoryViews',
            inverse: 'emojiCategoryBarViewOwner',
            isCausal: true,
        }),
        emojiPickerViewOwner: one('EmojiPickerView', {
            inverse: 'emojiCategoryBarView',
            readonly: true,
            required: true,
        }),
    },
});
