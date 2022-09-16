/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'EmojiGridItemView',
    fields: {
        emojiOrEmojiInCategory: one('EmojiOrEmojiInCategory', {
            identifying: true,
            inverse: 'emojiGridItemViews',
        }),
        emojiGridRowViewOwner: one('EmojiGridRowView', {
            identifying: true,
            inverse: 'items',
        }),
        emojiView: one('EmojiView', {
            compute() {
                if (this.emojiOrEmojiInCategory.emoji) {
                    return { emoji: this.emojiOrEmojiInCategory.emoji };
                }
                if (this.emojiOrEmojiInCategory.emojiInCategory) {
                    return { emoji: this.emojiOrEmojiInCategory.emojiInCategory.emoji };
                }
                return clear();
            },
            inverse: 'emojiGridItemViewOwner',
        }),
        width: attr({
            compute() {
                if (!this.emojiGridRowViewOwner.emojiGridViewOwner) {
                    return clear();
                }
                return this.emojiGridRowViewOwner.emojiGridViewOwner.itemWidth;
            },
            default: 0,
        }),
    },
});
