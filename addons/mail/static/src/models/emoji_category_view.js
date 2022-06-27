/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { replace } from '@mail/model/model_field_command';

registerModel({
    name: 'EmojiCategoryView',
    identifyingFields: ['emojiCategory', 'emojiCategoryBar'],
    recordMethods: {
        /** 
         * @param {MouseEvent} ev
         */
        onClick() {
            this.emojiCategory.emojiRegistry.update({ currentCategory: replace(this.emojiCategory) });
        },
    },
    fields: {
        emojiCategory: one('EmojiCategory', {
            inverse: 'emojiCategoryViews',
            readonly: true,
            required: true,
        }),
        emojiCategoryBar: one('EmojiCategoryBar', {
            inverse: 'emojiCategoryViews',
            readonly: true,
            required: true,
        }),
    }
});
