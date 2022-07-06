/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { replace } from '@mail/model/model_field_command';

registerModel({
    name: 'EmojiCategory',
    identifyingFields: ['name'],
    recordMethods: {
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
        emojiCategoryViews: many('EmojiCategoryView', {
            inverse: 'emojiCategory',
            isCausal: true,
        }),
        emojiRegistry: one("EmojiRegistry", {
            compute: '_computeEmojiRegistry',
            inverse: "allCategories",
            required: true,
        }),
        name: attr({
            readonly: true,
            required: true,
        }),
        sortId: attr({
            readonly: true,
            required: true,
        }),
        title: attr({
            readonly: true,
            required: true,
        }),
    },
});
