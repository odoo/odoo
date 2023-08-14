odoo.define('mail/static/src/models/thread_partner_seen_info/thread_partner_seen_info.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2one } = require('mail/static/src/model/model_field.js');

function factory(dependencies) {

    class ThreadPartnerSeenInfo extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
        static _createRecordLocalId(data) {
            const { channelId, partnerId } = data;
            return `${this.modelName}_${channelId}_${partnerId}`;
        }

        /**
         * @private
         * @returns {mail.partner|undefined}
         */
        _computePartner() {
            return [['insert', { id: this.partnerId }]];
        }

        /**
         * @private
         * @returns {mail.thread|undefined}
         */
        _computeThread() {
            return [['insert', {
                id: this.channelId,
                model: 'mail.channel',
            }]];
        }

    }

    ThreadPartnerSeenInfo.modelName = 'mail.thread_partner_seen_info';

    ThreadPartnerSeenInfo.fields = {
        /**
         * The id of channel this seen info is related to.
         *
         * Should write on this field to set relation between the channel and
         * this seen info, not on `thread`.
         *
         * Reason for not setting the relation directly is the necessity to
         * uniquely identify a seen info based on channel and partner from data.
         * Relational data are list of commands, which is problematic to deduce
         * identifying records.
         *
         * TODO: task-2322536 (normalize relational data) & task-2323665
         * (required fields) should improve and let us just use the relational
         * fields.
         */
        channelId: attr(),
        lastFetchedMessage: many2one('mail.message'),
        lastSeenMessage: many2one('mail.message'),
        /**
         * Partner that this seen info is related to.
         *
         * Should not write on this field to update relation, and instead
         * should write on @see partnerId field.
         */
        partner: many2one('mail.partner', {
            compute: '_computePartner',
            dependencies: ['partnerId'],
        }),
        /**
         * The id of partner this seen info is related to.
         *
         * Should write on this field to set relation between the partner and
         * this seen info, not on `partner`.
         *
         * Reason for not setting the relation directly is the necessity to
         * uniquely identify a seen info based on channel and partner from data.
         * Relational data are list of commands, which is problematic to deduce
         * identifying records.
         *
         * TODO: task-2322536 (normalize relational data) & task-2323665
         * (required fields) should improve and let us just use the relational
         * fields.
         */
        partnerId: attr(),
        /**
         * Thread (channel) that this seen info is related to.
         *
         * Should not write on this field to update relation, and instead
         * should write on @see channelId field.
         */
        thread: many2one('mail.thread', {
            compute: '_computeThread',
            dependencies: ['channelId'],
            inverse: 'partnerSeenInfos',
        }),
    };

    return ThreadPartnerSeenInfo;
}

registerNewModel('mail.thread_partner_seen_info', factory);

});
