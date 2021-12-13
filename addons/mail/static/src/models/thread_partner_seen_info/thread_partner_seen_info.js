/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many2one } from '@mail/model/model_field';

registerModel({
    name: 'ThreadPartnerSeenInfo',
    identifyingFields: ['thread', 'partner'],
    fields: {
        lastFetchedMessage: many2one('Message'),
        lastSeenMessage: many2one('Message'),
        /**
         * Partner that this seen info is related to.
         */
        partner: many2one('Partner', {
            inverse: 'partnerSeenInfos',
            readonly: true,
            required: true,
        }),
        /**
         * Thread (channel) that this seen info is related to.
         */
        thread: many2one('Thread', {
            inverse: 'partnerSeenInfos',
            readonly: true,
            required: true,
        }),
    },
});
