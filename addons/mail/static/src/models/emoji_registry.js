/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many, one } from '@mail/model/model_field';
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
            inverse: 'emojiRegistry',
        }),
        allEmojis: many('Emoji', {
            inverse: 'emojiRegistry',
            sort() {
                return [['smaller-first', 'codepoints']];
            }
        }),
        allFrequentlyUsedEmojis: many('Emoji', {
            compute() {
                if (this.allUsedEmojis.length < 42) {
                    return this.allUsedEmojis;
                }
                return this.allUsedEmojis.slice(0, 42);
            },
            inverse: 'emojiRegistryAsFrequentlyUsed',
        }),
        allUsedEmojis: many('Emoji', {
            inverse: 'emojiRegistryAsUsedEmoji',
            sort() {
                return [['greater-first', 'useAmount']];
            },
        }),
        allVisibleCategories: many('EmojiCategory', {
            inverse: 'emojiRegistryAsVisible',
            sort() {
                return [['smaller-first', 'sortId']];
            },
        }),
        dataCategories: many('EmojiCategory'),
        frequentlyUsedCategory: one('EmojiCategory', {
            default: { name: "Frequently Used", sortId: 0, title: '🕘' },
        }),
    },
});
