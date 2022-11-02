/** @odoo-module **/

import { attr, clear, one, Model } from '@mail/model';

Model({
    name: 'EmojiView',
    template: 'mail.EmojiView',
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        onClick(ev) {
            this.sendEmoji();
        },
        /**
         * @param {MouseEvent} ev
         */
        onMouseenter(ev) {
            if (!this.exists()) {
                return;
            }
            this.update({ emojiGridViewAsLastSelected: this.emojiGridRowViewOwner.emojiGridViewOwner });
        },
        /**
         * @param {MouseEvent} ev
         */
        onMouseleave(ev) {
            if (!this.exists()) {
                return;
            }
            this.update({ emojiGridViewAsHovered: clear() });
        },
        sendEmoji() {
            if (!this.emojiGridRowViewOwner) {
                return;
            }
            if (this.emojiPickerViewOwner.popoverViewOwner.messageActionViewOwnerAsReaction) {
                this.emojiPickerViewOwner.popoverViewOwner.messageActionViewOwnerAsReaction.onClickReaction({ codepoints: this.emoji.codepoints });
                return;
            }
            if (this.emojiPickerViewOwner.popoverViewOwner.composerViewOwnerAsEmoji) {
                this.emojiPickerViewOwner.popoverViewOwner.composerViewOwnerAsEmoji.onClickEmoji({ codepoints: this.emoji.codepoints });
                return;
            }
        },
    },
    fields: {
        emoji: one('Emoji', { inverse: 'emojiViews',
            compute() {
                if (this.emojiOrEmojiInCategory.emoji) {
                    return this.emojiOrEmojiInCategory.emoji;
                }
                if (this.emojiOrEmojiInCategory.emojiInCategory) {
                    return this.emojiOrEmojiInCategory.emojiInCategory.emoji;
                }
                return clear();
            },
        }),
        emojiGridViewAsLastSelected: one('EmojiGridView', { inverse: 'lastSelectedEmojiView' }),
        emojiGridViewAsSelected: one('EmojiGridView', { inverse: 'selectedEmojiView' }),
        emojiOrEmojiInCategory: one('EmojiOrEmojiInCategory', { identifying: true, inverse: 'emojiViews' }),
        emojiGridRowViewOwner: one('EmojiGridRowView', { identifying: true, inverse: 'items' }),
        emojiPickerViewOwner: one('EmojiPickerView', {
            compute() {
                return this.emojiGridRowViewOwner.emojiGridViewOwner.emojiPickerViewOwner;
            }
        }),
        index: attr(),
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
