/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'FollowerSubtypeView',
    identifyingFields: ['followerSubtypeListOwner', 'subtype'],
    fields: {
        followerSubtypeListOwner: one('FollowerSubtypeList', {
            inverse: 'followerSubtypeViews',
            readonly: true,
            required: true,
        }),
        subtype: one('FollowerSubtype', {
            inverse: 'followerSubtypeViews',
            readonly: true,
            required: true,
        }),
    },
});
