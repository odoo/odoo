/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'Emoji',
    identifyingFields: ['unicode'],
    recordMethods: {
        /**
         * @returns {string|FieldCommand}
         */
        _computeDisplayCodepoints() {
            if (!this.emojiRegistry) {
                return clear();
            }
            if (!this.hasSkinToneVariations || this.emojiRegistry.skinTone === 0) {
                return this.unicode;
            }
            const skinToneCodepoint = (() => {
                switch (this.emojiRegistry.skinTone) {
                    case 1:
                        return '\u{1F3FB}';
                    case 2:
                        return '\u{1F3FC}';
                    case 3:
                        return '\u{1F3FD}';
                    case 4:
                        return '\u{1F3FE}';
                    case 5:
                        return '\u{1F3FF}';
                }
            })();
            const [base, ...rest] = this.unicode;
            return [base, skinToneCodepoint, ...rest].join('');
        },
        _computeEmojiRegistry() {
            return replace(this.messaging.emojiRegistry);
        },
    },
    fields: {
        description: attr({
            readonly: true,
        }),
        displayCodepoints: attr({
            compute: '_computeDisplayCodepoints',
        }),
        emojiCategories: many('EmojiCategory', {
            inverse: 'allEmojis',
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
        sources: attr({
            readonly: true,
        }),
        unicode: attr({
            readonly: true,
            required: true,
        }),
    },
});
