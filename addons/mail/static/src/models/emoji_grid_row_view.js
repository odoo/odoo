/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'EmojiGridRowView',
    template: 'mail.EmojiGridRowView',
    fields: {
        category: one('EmojiCategory', { related: 'viewCategory.category' }),
        emojiGridViewOwner: one('EmojiGridView', { related: 'emojiGridViewRowRegistryOwner.emojiGridViewOwner' }),
        hasSection: attr({ default: false,
            compute() {
                if (this.viewCategory) {
                    return true;
                }
                return clear();
            },
        }),
        index: attr({ identifying: true }),
        items: many('EmojiGridItemView', { inverse: 'emojiGridRowViewOwner' }),
        emojiGridViewRowRegistryOwner: one('EmojiGridViewRowRegistry', { identifying: true, inverse: 'rows' }),
        viewCategory: one('EmojiPickerView.Category', { inverse: 'emojiGridRowView' }),
    },
});
