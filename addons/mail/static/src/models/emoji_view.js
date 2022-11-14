/** @odoo-module **/

import { attr, clear, one, Model } from "@mail/model";

Model({
    name: "EmojiView",
    template: "mail.EmojiView",
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        onClick(ev) {
            if (!this.emojiGridRowViewOwner) {
                return;
            }
            if (this.emojiPickerViewOwner.popoverViewOwner.messageActionViewOwnerAsReaction) {
                this.emojiPickerViewOwner.popoverViewOwner.messageActionViewOwnerAsReaction.onClickReaction(
                    ev
                );
                return;
            }
            if (this.emojiPickerViewOwner.popoverViewOwner.composerViewOwnerAsEmoji) {
                this.emojiPickerViewOwner.popoverViewOwner.composerViewOwnerAsEmoji.onClickEmoji(
                    ev
                );
                return;
            }
        },
        /**
         * @param {MouseEvent} ev
         */
        onMouseenter(ev) {
            if (!this.exists()) {
                return;
            }
            this.update({ emojiGridViewAsHovered: this.emojiGridRowViewOwner.emojiGridViewOwner });
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
    },
    fields: {
        emoji: one("Emoji", {
            inverse: "emojiViews",
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
        emojiGridViewAsHovered: one("EmojiGridView", { inverse: "hoveredEmojiView" }),
        emojiOrEmojiInCategory: one("EmojiOrEmojiInCategory", {
            identifying: true,
            inverse: "emojiViews",
        }),
        emojiGridRowViewOwner: one("EmojiGridRowView", { identifying: true, inverse: "items" }),
        emojiPickerViewOwner: one("EmojiPickerView", {
            compute() {
                return this.emojiGridRowViewOwner.emojiGridViewOwner.emojiPickerViewOwner;
            },
        }),
        width: attr({
            default: 0,
            compute() {
                if (!this.emojiGridRowViewOwner.emojiGridViewOwner) {
                    return clear();
                }
                return this.emojiGridRowViewOwner.emojiGridViewOwner.itemWidth;
            },
        }),
    },
});
