/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many, one } from '@mail/model/model_field';

registerModel({
    name: 'EmojiPickerHeaderActionListView',
    fields: {
        __dummyActionView: one('EmojiPickerHeaderActionView', {
            inverse: '__ownerAsDummy',
        }),
        actionViews: many('EmojiPickerHeaderActionView', {
            inverse: 'owner',
            sort() {
                return [
                    ['smaller-first', 'sequence'],
                ];
            },
        }),
        emojiPickerView: one('EmojiPickerView', {
            related: 'owner.emojiPickerViewOwner',
        }),
        owner: one('EmojiPickerHeaderView', {
            identifying: true,
            inverse: 'actionListView',
        }),
    },
});
