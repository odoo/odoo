/** @odoo-module **/

import { attr, clear, many, one, Model } from "@mail/model";

Model({
    name: "EmojiGridRowView",
    template: "mail.EmojiGridRowView",
    fields: {
        category: one("EmojiCategory", { related: "viewCategory.category" }),
        emojiGridViewOwner: one("EmojiGridView", {
            related: "emojiGridViewRowRegistryOwner.emojiGridViewOwner",
        }),
        hasSection: attr({
            default: false,
            compute() {
                if (this.viewCategory) {
                    return true;
                }
                return clear();
            },
        }),
        index: attr({ identifying: true }),
        items: many("EmojiView", { inverse: "emojiGridRowViewOwner" }),
        emojiGridViewRowRegistryOwner: one("EmojiGridViewRowRegistry", {
            identifying: true,
            inverse: "rows",
        }),
        viewCategory: one("EmojiPickerView.Category", { inverse: "emojiGridRowView" }),
    },
});
