/** @odoo-module **/

import { registerModel } from "@mail/model/model_core";
import { many, one } from "@mail/model/model_field";
import { clear } from "@mail/model/model_field_command";

registerModel({
    name: "EmojiCategoryBarView",
    template: "mail.EmojiCategoryBarView",
    templateGetter: "emojiCategoryBarView",
    fields: {
        emojiCategoryViews: many("EmojiCategoryView", {
            inverse: "emojiCategoryBarViewOwner",
            compute() {
                if (!this.emojiPickerView) {
                    return clear();
                }
                return this.emojiPickerView.categories.map((category) => ({
                    viewCategory: category,
                }));
            },
        }),
        emojiPickerHeaderViewOwner: one("EmojiPickerHeaderView", {
            identifying: true,
            inverse: "emojiCategoryBarView",
        }),
        emojiPickerView: one("EmojiPickerView", {
            related: "emojiPickerHeaderViewOwner.emojiPickerViewOwner",
        }),
    },
});
