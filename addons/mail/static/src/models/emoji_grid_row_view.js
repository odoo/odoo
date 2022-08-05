/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'EmojiGridRowView',
    fields: {
        emojiGridViewOwner: one('EmojiGridView', {
            related: 'emojiGridViewRowRegistryOwner.emojiGridViewOwner',
        }),
        index: attr({
            identifying: true,
        }),
        items: many('EmojiGridItemView', {
            isCausal: true,
            inverse: 'emojiGridRowViewOwner',
        }),
        sectionView: one('EmojiGridSectionView', {
            compute() {
                if (this.viewCategory) {
                    return {};
                }
                return clear();
            },
            isCausal: true,
            inverse: 'emojiGridRowViewOwner',
        }),
        emojiGridViewRowRegistryOwner: one('EmojiGridViewRowRegistry', {
            identifying: true,
            inverse: 'rows',
        }),
        viewCategory: one('EmojiPickerView.Category', {
            inverse: 'emojiGridRowView',
        }),
    },
});
