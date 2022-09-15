/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many } from '@mail/model/model_field';
import { insert } from '@mail/model/model_field_command';
import { emojiCategoriesData, emojisData } from '@mail/models_data/emoji_data';

registerModel({
    name: 'EmojiRegistry',
    lifecycleHooks: {
        _created() {
            this._populateFromEmojiData(emojiCategoriesData, emojisData);
        },
    },
    recordMethods: {
        async _populateFromEmojiData(dataCategories, dataEmojis) {
            await this.messaging.executeGracefully(dataCategories.map(category => () => {
                if (!this.exists()) {
                    return;
                }
                const emojiCount = dataEmojis.reduce((acc, emoji) => emoji.category === category.name ? acc + 1 : acc, 0);
                this.update({
                    dataCategories: insert({
                        name: category.name,
                        title: category.title,
                        sortId: category.sortId,
                        emojiCount,
                    }),
                });
            }));
            if (!this.exists()) {
                return;
            }
            await this.messaging.executeGracefully(dataEmojis.map(emojiData => () => {
                if (!this.exists()) {
                    return;
                }
                this.models['Emoji'].insert({
                    codepoints: emojiData.codepoints,
                    shortcodes: emojiData.shortcodes,
                    emoticons: emojiData.emoticons,
                    name: emojiData.name,
                    keywords: emojiData.keywords,
                    emojiDataCategory: { name: emojiData.category },
                });
            }));
        },
    },
    fields: {
        allCategories: many('EmojiCategory', {
            compute() {
                return this.dataCategories;
            },
            inverse: 'emojiRegistry',
            sort() {
                return [['smaller-first', 'sortId']];
            },
        }),
        allEmojis: many('Emoji', {
            inverse: 'emojiRegistry',
            sort() {
                return [['smaller-first', 'codepoints']];
            }
        }),
        dataCategories: many('EmojiCategory'),
    },
});
