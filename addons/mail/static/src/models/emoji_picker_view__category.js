/** @odoo-module **/

import { attr, clear, one, Model } from "@mail/model";

/**
 * Emoji category info of a specific emoji picker view
 */
Model({
    name: "EmojiPickerView.Category",
    fields: {
        category: one("EmojiCategory", {
            identifying: true,
            inverse: "allEmojiPickerViewCategory",
        }),
        emojiPickerViewOwner: one("EmojiPickerView", { identifying: true, inverse: "categories" }),
        emojiPickerViewAsActive: one("EmojiPickerView", { inverse: "activeCategory" }),
        emojiCategoryView: one("EmojiCategoryView", { inverse: "viewCategory" }),
        emojiGridRowView: one("EmojiGridRowView", { inverse: "viewCategory" }),
        emojiPickerViewOwnerAsLastCategory: one("EmojiPickerView", {
            compute() {
                if (
                    this.emojiPickerViewOwner.categories[
                        this.emojiPickerViewOwner.categories.length - 1
                    ] === this
                ) {
                    return this.emojiPickerViewOwner;
                }
                return clear();
            },
        }),
        endSectionIndex: attr({
            default: 0,
            compute() {
                if (!this.nextViewCategory || !this.nextViewCategory.emojiGridRowView) {
                    return clear();
                }
                return this.nextViewCategory.emojiGridRowView.index - 1;
            },
        }),
        nextViewCategory: one("EmojiPickerView.Category", {
            compute() {
                const index = this.emojiPickerViewOwner.categories.findIndex(
                    (category) => category === this
                );
                if (index === -1) {
                    return clear();
                }
                if (index === this.emojiPickerViewOwner.categories.length - 1) {
                    return clear();
                }
                return this.emojiPickerViewOwner.categories[index + 1];
            },
        }),
    },
});
