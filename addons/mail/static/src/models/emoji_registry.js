/** @odoo-module **/

import { attr, insert, many, Model } from "@mail/model";
import { getBundle, loadBundle } from "@web/core/assets";

Model({
    name: "EmojiRegistry",
    recordMethods: {
        async loadEmojiData() {
            this.update({ isLoading: true });
            await getBundle("mail.assets_model_data").then(loadBundle);
            const { categories, emojis } = await odoo.runtimeImport(
                "@mail/new/utils/emoji/emoji_data"
            );
            if (!this.exists()) {
                return;
            }
            this._populateFromEmojiData(categories, emojis);
        },
        async _populateFromEmojiData(dataCategories, dataEmojis) {
            dataCategories.map((category) => {
                this.update({
                    dataCategories: insert({
                        name: category.name,
                        title: category.title,
                        sortId: category.sortId,
                    }),
                });
            });
            this.models["Emoji"].insert(
                dataEmojis.map((emojiData) => ({
                    codepoints: emojiData.codepoints,
                    shortcodes: emojiData.shortcodes,
                    emoticons: emojiData.emoticons,
                    name: emojiData.name,
                    keywords: emojiData.keywords,
                    emojiDataCategory: { name: emojiData.category },
                }))
            );
            this.update({
                isLoaded: true,
                isLoading: false,
            });
        },
    },
    fields: {
        allCategories: many("EmojiCategory", {
            inverse: "emojiRegistry",
            compute() {
                return this.dataCategories;
            },
            sort: [["smaller-first", "sortId"]],
        }),
        allEmojis: many("Emoji", {
            inverse: "emojiRegistry",
            sort: [["smaller-first", "codepoints"]],
        }),
        dataCategories: many("EmojiCategory"),
        isLoaded: attr({ default: false }),
        isLoading: attr({ default: false }),
    },
});
