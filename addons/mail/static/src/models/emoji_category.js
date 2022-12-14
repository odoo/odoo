/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';

registerModel({
    name: 'EmojiCategory',
    fields: {
        allEmojiInCategoryOfCurrent: many('EmojiInCategory', {
            inverse: 'category',
        }),
        allEmojiPickerViewCategory: many('EmojiPickerView.Category', {
            inverse: 'category',
        }),
        allEmojis: many('Emoji', {
            inverse: 'emojiCategories',
        }),
        displayName: attr(),
        emojiCount: attr({ //Number of emojis that will be in that category once every emoji is loaded.
            default: 0,
        }),
        emojiRegistry: one("EmojiRegistry", {
            compute() {
                return this.messaging.emojiRegistry;
            },
            inverse: "allCategories",
            required: true,
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
