/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many, one } from '@mail/model/model_field';
import { insertAndReplace, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'EmojiCategoryBar',
    identifyingFields: ['emojiPickerView'],
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
            inverse: 'emojiCategoryBar',
            readonly: true,
            isCausal: true,
        }),
        emojiPickerView: one('EmojiPickerView', {
            inverse: 'emojiCategoryBar',
            readonly: true,
            required: true,
        }),
    },
});
