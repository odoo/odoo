/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many } from '@mail/model/model_field';
import { insert } from '@mail/model/model_field_command';
import { emojiCategoriesData, emojisData } from '@mail/models_data/emoji_data';
import { executeGracefully } from '@mail/utils/utils';

registerModel({
    name: 'EmojiRegistry',
    lifecycleHooks: {
        _created() {
            this._populateFromEmojiData(emojiCategoriesData, emojisData);
        },
    },
    recordMethods: {
        async _populateFromEmojiData(dataCategories, dataEmojis) {
            await executeGracefully(dataCategories.map(category => () => {
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
            this.update({ allEmojiCount: dataEmojis.length }); // Set the total number of emojis to the category before all emojis are processed and created.
            await executeGracefully(dataEmojis.map(emojiData => () => {
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
        _sortAllCategories() {
            return [['smaller-first', 'sortId']];
        },
        _sortAllEmojis() {
            return [['smaller-first', 'codepoints']];
        }
    },
    fields: {
        allCategories: many('EmojiCategory', {
            compute() {
                return this.dataCategories;
            },
            inverse: 'emojiRegistry',
            sort: '_sortAllCategories',
        }),
        allEmojiCount: attr({
            default: 0,
        }),
        allEmojis: many('Emoji', {
            inverse: 'emojiRegistry',
            sort: '_sortAllEmojis'
        }),
        dataCategories: many('EmojiCategory'),
    },
});
