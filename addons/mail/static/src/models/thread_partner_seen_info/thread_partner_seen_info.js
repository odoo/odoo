odoo.define('mail/static/src/models/thread_partner_seen_info/thread_partner_seen_info.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2one } = require('mail/static/src/model/model_field.js');

function factory(dependencies) {

    class ThreadPartnerSeenInfo extends dependencies['mail.model'] {}

    ThreadPartnerSeenInfo.modelName = 'mail.thread_partner_seen_info';

    ThreadPartnerSeenInfo.fields = {
        id: attr(),
        lastFetchedMessage: many2one('mail.message'),
        lastSeenMessage: many2one('mail.message'),
        partner: many2one('mail.partner'),
        thread: many2one('mail.thread', {
            inverse: 'partnerSeenInfos',
        }),
    };

    return ThreadPartnerSeenInfo;
}

registerNewModel('mail.thread_partner_seen_info', factory);

});
