/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many2one, one2one } from '@mail/model/model_field';

registerModel({
    name: 'mail.follower_subtype_list',
    identifyingFields: ['follower'],
    fields: {
        /**
         * States the dialog displaying this follower subtype list.
         */
        dialog: one2one('mail.dialog', {
            inverse: 'followerSubtypeList',
            isCausal: true,
            readonly: true,
        }),
        follower: many2one('mail.follower', {
            inverse: 'subtypeList',
            readonly: true,
            required: true,
        }),
    },
});
