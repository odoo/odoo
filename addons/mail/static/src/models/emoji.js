/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'Emoji',
    recordMethods: {
        /**
         * Compares two strings
         *
         * @private
         * @returns {boolean}
         */
        _fuzzySearch(string, search) {
            let i = 0;
            let j = 0;
            while (i < string.length) {
                if (string[i] === search[j]) {
                    j += 1;
                }
                if (j === search.length) {
                    return true;
                }
                i += 1;
            }
            return false;
        },
        /**
         * @private
         * @returns {boolean}
         */
        _isStringInEmojiKeywords(string) {
            for (let index in this.searchData) {
                if (this._fuzzySearch(this.searchData[index], string)) { //If at least one correspondence is found, return true.
                    return true;
                }
            }
            return false;
        },
    },
    fields: {
        allEmojiInCategoryOfCurrent: many('EmojiInCategory', {
            compute() {
                return this.emojiCategories.map(category => ({ category }));
            },
            inverse: 'emoji',
        }),
        codepoints: attr({
            identifying: true,
        }),
        emojiCategories: many('EmojiCategory', {
            compute() {
                if (!this.emojiRegistry) {
                    return clear();
                }
                return [this.emojiDataCategory];
            },
            inverse: 'allEmojis',
        }),
        emojiDataCategory: one('EmojiCategory'),
        emojiOrEmojiInCategory: many('EmojiOrEmojiInCategory', {
            inverse: 'emoji',
        }),
        emojiRegistry: one('EmojiRegistry', {
            compute() {
                if (!this.messaging) {
                    return clear();
                }
                return this.messaging.emojiRegistry;
            },
            inverse: 'allEmojis',
            required: true,
        }),
        emojiViews: many('EmojiView', {
            inverse: 'emoji',
            readonly: true,
        }),
        emoticons: attr(),
        keywords: attr(),
        name: attr({
            readonly: true,
        }),
        searchData: attr({
            compute() {
                return [...this.shortcodes, ...this.emoticons, ...this.name, ...this.keywords];
            },
        }),
        shortcodes: attr(),
        sources: attr({
            compute() {
                return [...this.shortcodes, ...this.emoticons];
            },
        }),
    },
});
