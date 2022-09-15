/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many } from '@mail/model/model_field';
import { insert } from '@mail/model/model_field_command';

registerModel({
    name: 'EmojiRegistry',
    lifecycleHooks: {
        _created() {
            if (!this.messaging.isInQUnitTest && !this.hasEmojiDataLoaded && !this.isFetchingEmojiData) {
                this.fetchEmojiData();
            }
        }
    },
    recordMethods: {
        async fetchEmojiData() {
            if (!this.exists()) {
                return;
            }
            this.update({ isFetchingEmojiData: true });
            const response = await fetch('/mail/emoji/get_data');
            if (!this.exists()) {
                return;
            }
            const emojiDataJSContent = await response.text();
            if (!this.exists()) {
                return;
            }
            const script = document.createElement('script');
            script.innerHTML = emojiDataJSContent;
            document.head.appendChild(script);
            this.update({ isFetchingEmojiData: false });
        },
        async populateFromEmojiData(dataCategories, dataEmojis) {
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
            this.update({ hasEmojiDataLoaded: true });
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
        hasEmojiDataLoaded: attr({
            default: false,
        }),
        isFetchingEmojiData: attr({
            default: false,
        }),
    },
});
