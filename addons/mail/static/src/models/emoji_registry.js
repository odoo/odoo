/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many, one } from '@mail/model/model_field';
import { insert, insertAndReplace, replace } from '@mail/model/model_field_command';
import { emojiCategoriesData, emojisData } from '@mail/models_data/emoji_data';
import { executeGracefully } from '@mail/utils/utils';

registerModel({
    name: 'EmojiRegistry',
    identifyingFields: ['messaging'],
    lifecycleHooks: {
        _created() {
            this._populateFromEmojiData();
        },
    },
    recordMethods: {
        _computeAllCategories() {
            return replace([
                this.categoryAll,
                ...this.dataCategories,
            ]);
        },
        async _populateFromEmojiData() {
            await executeGracefully(emojiCategoriesData.map(category => () => {
                if (!this.exists()) {
                    return;
                }
                this.update({
                    dataCategories: insert({
                        name: category.name,
                        title: category.title,
                        sortId: category.sortId,
                    }),
                });
            }));
            await executeGracefully(emojisData.map(emojiData => () => {
                if (!this.exists()) {
                    return;
                }
                this.models['Emoji'].insert({
                    codepoints: emojiData.codepoints,
                    sources: [...emojiData.shortcodes, ...emojiData.emoticons],
                    name: emojiData.name,
                    emojiDataCategory: insertAndReplace(
                        { name: emojiData.category }
                    ),
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
            compute: '_computeAllCategories',
            inverse: 'emojiRegistry',
            sort: '_sortAllCategories',
        }),
        allEmojis: many('Emoji', {
            inverse: 'emojiRegistry',
            sort: '_sortAllEmojis'
        }),
        categoryAll: one('EmojiCategory', {
            default: insertAndReplace({ name: 'all', title: 'all', sortId: 0 }),
        }),
        dataCategories: many('EmojiCategory', {
        }),
    },
});
