/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
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

        _computeSkinToneCodepoint() {
            switch (this.skinTone) {
                case 1:
                    return '\u{1F3FB}';
                case 2:
                    return '\u{1F3FC}';
                case 3:
                    return '\u{1F3FD}';
                case 4:
                    return '\u{1F3FE}';
                case 5:
                    return '\u{1F3FF}';
                default:
                    return '';
            }
        },
        async _populateFromEmojiData() {
            await executeGracefully(emojiCategoriesData.map(category => () => {
                this.update({
                    dataCategories: insert({
                        name: category.name,
                        title: category.title,
                        sortId: category.sortId,
                    }),
                });
            }));
            await executeGracefully(emojisData.map(emojiData => () => {
                this.models['Emoji'].insert({
                    codepoints: emojiData.codepoints,
                    sources: [...emojiData.shortcodes, ...emojiData.emoticons],
                    name: emojiData.name,
                    emojiDataCategory: insertAndReplace(
                        { name: emojiData.category }
                    ),
                    hasSkinToneVariations: emojiData.hasSkinToneVariations,
                });
            }));
        },
        _sortAllCategories() {
            return [['smaller-first', 'sortId']];
        },
        _sortAllEmojis() {
            return [['smaller-first', 'codepointsRepresentation']];
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
        skinTone: attr({
            default: 0,
        }),
        skinToneCodepoint: attr({
            compute: '_computeSkinToneCodepoint',
        }),
    },
});
