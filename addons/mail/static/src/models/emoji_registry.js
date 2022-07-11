/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many } from '@mail/model/model_field';
import { insert } from '@mail/model/model_field_command';
import { emojiData } from '@mail/models_data/emoji_data';

registerModel({
    name: 'EmojiRegistry',
    identifyingFields: ['messaging'],
    lifecycleHooks: {
        _created() {
            this._populateFromEmojiData();
        },
    },
    recordMethods: {
        _populateFromEmojiData() {
            this.models['Emoji'].insert(emojiData.map(emoji => {
                return {
                    unicode: emoji.codepoints,
                    sources: [...emoji.shortcodes, ...emoji.emoticons],
                    keywords: [...emoji.shortcodes, ...emoji.emoticons, ...emoji.name, ...emoji.keywords],
                    description: emoji.name,
                    emojiCategories: insert([
                        { categoryName: "all" },
                        { categoryName: emoji.category },
                    ]),
                    hasSkinToneVariations: emoji.hasSkinToneVariations,
                };
            }));
        },
    },
    fields: {
        allCategories: many('EmojiCategory', {
            inverse: 'emojiRegistry',
        }),
        allEmojis: many('Emoji', {
            inverse: 'emojiRegistry',
        }),
        skinTone: attr({
            default: 0,
        }),
    },
});
