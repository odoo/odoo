/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'EmojiSectionView',
    fields: {
        category: one('EmojiCategory', {
            related: 'emojiGridRowViewOwner.category',
        }),
        emojiGridRowViewOwner: one('EmojiGridRowView', {
            identifying: true,
            inverse: 'sectionView',
        }),
    },
});
