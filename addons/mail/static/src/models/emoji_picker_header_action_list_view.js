/** @odoo-module **/

import { many, one, registerModel } from '@mail/model';

registerModel({
    name: 'EmojiPickerHeaderActionListView',
    template: 'mail.EmojiPickerHeaderActionListView',
    templateGetter: 'emojiPickerHeaderActionListView',
    fields: {
        __dummyActionView: one('EmojiPickerHeaderActionView', { inverse: '__ownerAsDummy' }),
        actionViews: many('EmojiPickerHeaderActionView', { inverse: 'owner',
            sort: [['smaller-first', 'sequence']],
        }),
        emojiPickerView: one('EmojiPickerView', { related: 'owner.emojiPickerViewOwner' }),
        owner: one('EmojiPickerHeaderView', { identifying: true, inverse: 'actionListView' }),
    },
});
