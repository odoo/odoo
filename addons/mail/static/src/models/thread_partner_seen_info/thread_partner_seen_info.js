/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { many2one } from '@mail/model/model_field';

function factory(dependencies) {

    class ThreadPartnerSeenInfo extends dependencies['mail.model'] {
    }

    ThreadPartnerSeenInfo.fields = {
        lastFetchedMessage: many2one('mail.message'),
        lastSeenMessage: many2one('mail.message'),
        /**
         * Partner that this seen info is related to.
         */
        partner: many2one('mail.partner', {
            inverse: 'partnerSeenInfos',
            readonly: true,
            required: true,
        }),
        /**
         * Thread (channel) that this seen info is related to.
         */
        thread: many2one('mail.thread', {
            inverse: 'partnerSeenInfos',
            readonly: true,
            required: true,
        }),
    };
    ThreadPartnerSeenInfo.identifyingFields = ['thread', 'partner'];
    ThreadPartnerSeenInfo.modelName = 'mail.thread_partner_seen_info';

    return ThreadPartnerSeenInfo;
}

registerNewModel('mail.thread_partner_seen_info', factory);
