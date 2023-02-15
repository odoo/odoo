/** @odoo-module **/

import { many, one, Model } from "@mail/model";

Model({
    name: "EmojiOrEmojiInCategory",
    identifyingMode: "xor",
    fields: {
        emoji: one("Emoji", { identifying: true, inverse: "emojiOrEmojiInCategory" }),
        emojiInCategory: one("EmojiInCategory", {
            identifying: true,
            inverse: "emojiOrEmojiInCategory",
        }),
        emojiViews: many("EmojiView", { inverse: "emojiOrEmojiInCategory" }),
    },
});
