/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many } from '@mail/model/model_field';
import { insert } from '@mail/model/model_field_command';
import { getBundle, loadBundle } from '@web/core/assets';

registerModel({
    name: 'EmojiRegistry',
    recordMethods: {
        async loadEmojiData() {
            this.update({ isLoading: true });
            await getBundle('mail.assets_model_data').then(loadBundle);
            const { emojiCategoriesData, emojisData } = await odoo.runtimeImport("@mail/models_data/emoji_data");
            if (!this.exists()) {
                return;
            }
            this._populateFromEmojiData(emojiCategoriesData, emojisData);
        },
        async _populateFromEmojiData(dataCategories, dataEmojis) {
            dataCategories.map(category => {
                const emojiCount = dataEmojis.reduce((acc, emoji) => emoji.category === category.name ? acc + 1 : acc, 0);
                this.update({
                    dataCategories: insert({
                        name: category.name,
                        displayName: category.displayName,
                        title: category.title,
                        sortId: category.sortId,
                        emojiCount,
                    }),
                });
            });
            this.models['Emoji'].insert(dataEmojis.map(emojiData => ({
                codepoints: emojiData.codepoints,
                shortcodes: emojiData.shortcodes,
                emoticons: emojiData.emoticons,
                name: emojiData.name,
                keywords: emojiData.keywords,
                emojiDataCategory: { name: emojiData.category },
            })));
            this.update({
                isLoaded: true,
                isLoading: false,
            });
        },
    },
    fields: {
        allCategories: many('EmojiCategory', {
            compute() {
                return this.dataCategories;
            },
            inverse: 'emojiRegistry',
            sort: [['smaller-first', 'sortId']],
        }),
        allEmojis: many('Emoji', {
            inverse: 'emojiRegistry',
            sort: [['smaller-first', 'codepoints']],
        }),
        dataCategories: many('EmojiCategory'),
        isLoaded: attr({
            default: false,
        }),
        isLoading: attr({
            default: false,
        }),
    },
});
