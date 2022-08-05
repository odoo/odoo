/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'EmojiGridSectionView',
    fields: {
        category: one('EmojiCategory', {
            related: 'viewCategory.category',
        }),
        emojiGridRowViewOwner: one('EmojiGridRowView', {
            identifying: true,
            inverse: 'sectionView',
        }),
        viewCategory: one('EmojiPickerView.Category', {
            related: 'emojiGridRowViewOwner.viewCategory',
        }),
    },
});
