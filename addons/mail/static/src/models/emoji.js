/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { replace } from '@mail/model/model_field_command';

registerModel({
    name: 'Emoji',
    identifyingFields: ['codepoints'],
    recordMethods: {
        _computeEmojiRegistry() {
            return replace(this.messaging.emojiRegistry);
        },
        _computeEmojiCategories() {
            return replace([
                this.messaging.emojiRegistry.categoryAll,
                this.emojiDataCategory
            ]);
        },
    },
    fields: {
        codepoints: attr({
            readonly: true,
            required: true,
        }),
        emojiCategories: many('EmojiCategory', {
            compute: "_computeEmojiCategories",
            inverse: 'allEmojis',
        }),
        emojiDataCategory: one('EmojiCategory', {
        }),
        emojiRegistry: one('EmojiRegistry', {
            compute: '_computeEmojiRegistry',
            inverse: 'allEmojis',
            readonly: true,
            required: true,
        }),
        emojiViews: many('EmojiView', {
            inverse: 'emoji',
            readonly: true,
            isCausal: true,
        }),
        name: attr({
            readonly: true,
        }),
        sources: attr({
            readonly: true,
        }),
    },
});
