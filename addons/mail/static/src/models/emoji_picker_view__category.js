/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

/**
 * Emoji category info of a specific emoji picker view
 */
registerModel({
    name: 'EmojiPickerView.Category',
    fields: {
        category: one('EmojiCategory', {
            identifying: true,
            inverse: 'allEmojiPickerViewCategory',
        }),
        emojiPickerViewOwner: one('EmojiPickerView', {
            identifying: true,
            inverse: 'categories',
        }),
        emojiPickerViewAsActive: one('EmojiPickerView', {
            inverse: 'activeCategory',
        }),
        emojiCategoryView: one('EmojiCategoryView', {
            inverse: 'viewCategory',
            isCausal: true,
        }),
        emojiGridRowView: one('EmojiGridRowView', {
            inverse: 'viewCategory',
        }),
        endSectionIndex: attr({
            default: 0,
        }),
    },
});
