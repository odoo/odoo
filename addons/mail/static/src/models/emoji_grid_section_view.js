/** @odoo-module **/

import { one, registerModel } from '@mail/model';

registerModel({
    name: 'EmojiGridSectionView',
    template: 'mail.EmojiGridSectionView',
    templateGetter: 'emojiGridSectionView',
    fields: {
        category: one('EmojiCategory', { related: 'viewCategory.category' }),
        emojiGridRowViewOwner: one('EmojiGridRowView', { identifying: true, inverse: 'sectionView' }),
        viewCategory: one('EmojiPickerView.Category', { related: 'emojiGridRowViewOwner.viewCategory' }),
    },
});
