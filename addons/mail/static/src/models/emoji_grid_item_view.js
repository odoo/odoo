/** @odoo-module **/

import { attr, clear, one, registerModel } from '@mail/model';

registerModel({
    name: 'EmojiGridItemView',
    template: 'mail.EmojiGridItemView',
    templateGetter: 'emojiGridItemView',
    fields: {
        emojiOrEmojiInCategory: one('EmojiOrEmojiInCategory', { identifying: true, inverse: 'emojiGridItemViews' }),
        emojiGridRowViewOwner: one('EmojiGridRowView', { identifying: true, inverse: 'items' }),
        emojiView: one('EmojiView', { inverse: 'emojiGridItemViewOwner',
            compute() {
                if (this.emojiOrEmojiInCategory.emoji) {
                    return { emoji: this.emojiOrEmojiInCategory.emoji };
                }
                if (this.emojiOrEmojiInCategory.emojiInCategory) {
                    return { emoji: this.emojiOrEmojiInCategory.emojiInCategory.emoji };
                }
                return clear();
            },
        }),
        width: attr({ default: 0,
            compute() {
                if (!this.emojiGridRowViewOwner.emojiGridViewOwner) {
                    return clear();
                }
                return this.emojiGridRowViewOwner.emojiGridViewOwner.itemWidth;
            },
        }),
    },
});
