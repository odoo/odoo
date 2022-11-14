/** @odoo-module **/

import { many, one, Model } from "@mail/model";

Model({
    name: "EmojiInCategory",
    fields: {
        category: one("EmojiCategory", {
            identifying: true,
            inverse: "allEmojiInCategoryOfCurrent",
        }),
        emoji: one("Emoji", { identifying: true, inverse: "allEmojiInCategoryOfCurrent" }),
        emojiOrEmojiInCategory: many("EmojiOrEmojiInCategory", { inverse: "emojiInCategory" }),
    },
});
