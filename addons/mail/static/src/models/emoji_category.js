/** @odoo-module **/

import { attr, many, one, Model } from "@mail/model";

Model({
    name: "EmojiCategory",
    fields: {
        allEmojiInCategoryOfCurrent: many("EmojiInCategory", { inverse: "category" }),
        allEmojiPickerViewCategory: many("EmojiPickerView.Category", { inverse: "category" }),
        allEmojis: many("Emoji", { inverse: "emojiCategories" }),
        displayName: attr(),
        emojiRegistry: one("EmojiRegistry", {
            inverse: "allCategories",
            required: true,
            compute() {
                return this.messaging.emojiRegistry;
            },
        }),
        name: attr({ identifying: true }),
        sortId: attr({ readonly: true, required: true }),
        title: attr({ readonly: true, required: true }),
    },
});
