/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';

registerModel({
    name: 'Emoji',
    recordMethods: {
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeEmojiRegistry() {
            return this.messaging.emojiRegistry;
        },
    },
    fields: {
        description: attr({
            readonly: true,
        }),
        emojiCategories: many('EmojiCategory', {
            inverse: 'allEmojis',
        }),
        emojiRegistry: one('EmojiRegistry', {
            compute: '_computeEmojiRegistry',
            inverse: 'allEmojis',
            required: true,
        }),
        emojiViews: many('EmojiView', {
            inverse: 'emoji',
            readonly: true,
            isCausal: true,
        }),
        sources: attr({
            readonly: true,
        }),
        unicode: attr({
            identifying: true,
        }),
    },
});
