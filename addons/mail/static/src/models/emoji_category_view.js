/** @odoo-module **/

import { attr, one, Model } from "@mail/model";

Model({
    name: "EmojiCategoryView",
    template: "mail.EmojiCategoryView",
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        onClick() {
            this.emojiPickerViewOwner.reset();
            this.emojiPickerViewOwner.emojiGridView.update({
                categorySelectedByUser: this.viewCategory,
            });
        },
        /**
         * @param {MouseEvent} ev
         */
        onMouseenter(ev) {
            if (!this.exists()) {
                return;
            }
            this.update({ isHovered: true });
        },
        /**
         * @param {MouseEvent} ev
         */
        onMouseleave(ev) {
            if (!this.exists()) {
                return;
            }
            this.update({ isHovered: false });
        },
    },
    fields: {
        category: one("EmojiCategory", { related: "viewCategory.category" }),
        emojiPickerViewOwner: one("EmojiPickerView", {
            identifying: true,
            inverse: "emojiCategoryViews",
        }),
        isActive: attr({
            compute() {
                return Boolean(this.viewCategory.emojiPickerViewAsActive);
            },
        }),
        isHovered: attr({ default: false }),
        viewCategory: one("EmojiPickerView.Category", {
            identifying: true,
            inverse: "emojiCategoryView",
        }),
    },
});
