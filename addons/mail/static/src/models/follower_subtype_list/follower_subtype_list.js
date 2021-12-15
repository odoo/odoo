/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many2one, one2one } from '@mail/model/model_field';

registerModel({
    name: 'FollowerSubtypeList',
    identifyingFields: ['follower'],
    fields: {
        /**
         * States the dialog displaying this follower subtype list.
         */
        dialog: one2one('Dialog', {
            inverse: 'followerSubtypeList',
            isCausal: true,
            readonly: true,
        }),
        follower: many2one('Follower', {
            inverse: 'subtypeList',
            readonly: true,
            required: true,
        }),
    },
});
