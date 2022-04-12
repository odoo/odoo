/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'FollowerListMenuView',
    identifyingFields: [['chatterOwner']],
    fields: {
        chatterOwner: one('Chatter', {
            inverse: 'followerListMenuView',
            readonly: true,
        }),
        isDropdownOpen: attr({
            default: false,
        }),
    },
});
