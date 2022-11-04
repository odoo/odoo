/** @odoo-module **/

import { one, registerModel } from '@mail/model';

registerModel({
    name: 'EmojiPickerHeaderView',
    template: 'mail.EmojiPickerHeaderView',
    templateGetter: 'emojiPickerHeaderView',
    fields: {
        actionListView: one('EmojiPickerHeaderActionListView', { default: {}, isCausal: true, inverse: 'owner' }),
        emojiCategoryBarView: one('EmojiCategoryBarView', { default: {}, inverse: 'emojiPickerHeaderViewOwner', readonly: true, required: true }),
        emojiPickerViewOwner: one('EmojiPickerView', { identifying: true, inverse: 'headerView' }),
    },
});
