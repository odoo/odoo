/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'Emoji',
    identifyingFields: ['codepoints'],
    recordMethods: {
        /**
         * @returns {string|FieldCommand}
         */
        _computeCodepointsRepresentation() {
            if (!this.emojiRegistry) {
                return clear();
            }
            if (!this.hasSkinToneVariations || this.emojiRegistry.skinTone === 0) {
                return this.codepoints;
            }
            const [base, ...rest] = this.codepoints;
            return [base, this.emojiRegistry.skinToneCodepoint, ...rest].join('');
        },
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
        codepointsRepresentation: attr({
            compute: '_computeCodepointsRepresentation',
        }),
        defaultEmojiCategory: attr({
            default: "all"
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
        hasSkinToneVariations: attr(),
        name: attr({
            readonly: true,
        }),
        sources: attr({
            readonly: true,
        }),
    },
});
