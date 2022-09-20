/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'EmojiInCategory',
    fields: {
        category: one('EmojiCategory', {
            identifying: true,
            inverse: 'allEmojiInCategoryOfCurrent',
        }),
        emoji: one('Emoji', {
            identifying: true,
            inverse: 'allEmojiInCategoryOfCurrent',
        }),
        emojiOrEmojiInCategory: many('EmojiOrEmojiInCategory', {
            inverse: 'emojiInCategory',
        }),
        sequence: attr({
            compute() {
                if (!this.messaging || !this.messaging.emojiRegistry || !this.messaging.emojiRegistry.frequentlyUsedCategory) {
                    return clear();
                }
                if (this.category === this.messaging.emojiRegistry.frequentlyUsedCategory) {
                    return 1.0 / (this.emoji.useAmount + 1);
                }
                return parseInt(this.emoji.codepoints.substring(2), 16);
            },
            default: 0,
        }),
    },
});
