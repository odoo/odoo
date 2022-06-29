/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { replace } from '@mail/model/model_field_command';

registerModel({
    name: 'Emoji',
    identifyingFields: ['name'],
    recordMethods: {
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeEmojiRegistry() {
            return replace(this.messaging.emojiRegistry);
        },
    },
    fields: {
        description: attr({ //Field name in emoji_raw_data
            readonly: true
        }),
        emojiCategories: many('EmojiCategory', {
            inverse: 'allEmojis',
        }),
        emojiEmoticons: many('EmojiEmoticon', { //Field emoticons in emoji_raw_data
            inverse: 'emoji',
            readonly: true,
            isCausal: true,
        }),
        emojiKeywords: many('EmojiKeyword', { //Fieldkeywords in emoji_raw_data
            inverse: 'emoji',
            readonly: true,
            isCausal: true,
        }),
        emojiRegistry: one('EmojiRegistry', {
            compute: '_computeEmojiRegistry',
            inverse: 'allEmojis',
            readonly: true,
            required: true,
        }),
        emojiSkins: many('EmojiSkin', { //Field skins in emoji_raw_data
            inverse: 'emoji',
            readonly: true,
            isCausal: true,
        }),
        emojiViews: many('EmojiView', {
            inverse: 'emoji',
            readonly: true,
            isCausal: true,
        }),
        name: attr({ //Field ID in emoji_raw_data
            readonly: true,
            required: true,
        }),
    },
});
