/** @odoo-module **/

import { attr, clear, many, one, registerModel } from '@mail/model';

registerModel({
    name: 'EmojiGridRowView',
    template: 'mail.EmojiGridRowView',
    templateGetter: 'emojiGridRowView',
    fields: {
        emojiGridViewOwner: one('EmojiGridView', { related: 'emojiGridViewRowRegistryOwner.emojiGridViewOwner' }),
        index: attr({ identifying: true }),
        items: many('EmojiGridItemView', { inverse: 'emojiGridRowViewOwner' }),
        sectionView: one('EmojiGridSectionView', { inverse: 'emojiGridRowViewOwner',
            compute() {
                if (this.viewCategory) {
                    return {};
                }
                return clear();
            },
        }),
        emojiGridViewRowRegistryOwner: one('EmojiGridViewRowRegistry', { identifying: true, inverse: 'rows' }),
        viewCategory: one('EmojiPickerView.Category', { inverse: 'emojiGridRowView' }),
    },
});
