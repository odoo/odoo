/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'EmojiCategory',
    fields: {
        allEmojiInCategoryOfCurrent: many('EmojiInCategory', {
            inverse: 'category',
            sort() {
                return [['smaller-first', 'sequence']];
            },
        }),
        allEmojiPickerViewCategory: many('EmojiPickerView.Category', {
            inverse: 'category',
        }),
        allEmojis: many('Emoji', {
            inverse: 'emojiCategories',
        }),
        emojiCount: attr({ //Number of emojis that will be in that category once every emoji is loaded.
            default: 0,
        }),
        emojiRegistryAsVisible: one('EmojiRegistry', {
            compute() {
                if (this.allEmojis.length > 0) {
                    return this.emojiRegistry;
                }
                return clear();
            },
            inverse: 'allVisibleCategories',
        }),
        emojiRegistry: one("EmojiRegistry", {
            compute() {
                return this.messaging.emojiRegistry;
            },
            inverse: "allCategories",
        }),
        name: attr({
            identifying: true,
        }),
        sortId: attr({
            readonly: true,
            required: true,
        }),
        title: attr({
            readonly: true,
            required: true,
        }),
    },
});
