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
        saveFrequentlyUsedInLocalStorage() {
            this.update({ onSaveFrequentlyUsedInLocalStorageThrottle: {} });
        },
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
            // todo make the frequently used category
            for (const { codepoints, usage } of this.frequentlyUsedLocalStorageItem) {
                const emoji = this.models['Emoji'].findFromIdentifyingData({ codepoints });
                if (!emoji) {
                    continue;
                }
                emoji.update({ usage });
            }
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
        allEmojis: many('Emoji', {
            inverse: 'emojiRegistry',
            sort: '_sortAllEmojis'
        }),
        dataCategories: many('EmojiCategory'),
        frequentlyUsedLocalStorageItem: one('LocalStorageItem', {
            default: {},
            inverse: 'emojiRegistryAsFrequentlyUsed',
            isCausal: true,
        }),
        onSaveFrequentlyUsedInLocalStorageThrottle: one('Throttle', {
            compute() {
                return {
                    func: () => this.frequentlyUsedLocalStorageItem.update({
                        value: this.allEmojis.map(emoji => ({ codepoints: emoji.codepoints, usage: emoji.usage })),
                    }),
                };
            },
            inverse: 'emojiRegistryAsSaveFrequentlyUsedInLocalStorage',
            isCausal: true,
        }),
    },
});
