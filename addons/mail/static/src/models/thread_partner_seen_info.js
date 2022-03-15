/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'ThreadPartnerSeenInfo',
    identifyingFields: ['thread', 'partner'],
    fields: {
        lastFetchedMessage: one('Message'),
        lastSeenMessage: one('Message'),
        /**
         * Partner that this seen info is related to.
         */
        partner: one('Partner', {
            readonly: true,
            required: true,
        }),
        /**
         * Thread (channel) that this seen info is related to.
         */
        thread: one('Thread', {
            inverse: 'partnerSeenInfos',
            readonly: true,
            required: true,
        }),
    },
});
