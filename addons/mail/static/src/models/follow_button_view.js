/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'FollowButtonView',
    identifyingFields: [['chatterOwner']],
    fields: {
        chatterOwner: one('Chatter', {
            inverse: 'followButtonView',
            readonly: true,
        }),
        isUnfollowButtonHighlighted: attr({
            default: false,
        }),
    },
});
