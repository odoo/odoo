/** @odoo-module **/

import { one, registerModel } from '@mail/model';

registerModel({
    name: 'ThreadPartnerSeenInfo',
    fields: {
        lastFetchedMessage: one('Message'),
        lastSeenMessage: one('Message'),
        /**
         * Partner that this seen info is related to.
         */
        partner: one('Partner', { identifying: true }),
        /**
         * Thread (channel) that this seen info is related to.
         */
        thread: one('Thread', { inverse: 'partnerSeenInfos', identifying: true }),
    },
});
