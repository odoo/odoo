odoo.define('mail/static/src/models/thread_partner_seen_info/thread_partner_seen_info.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2one } = require('mail/static/src/model/model_field_utils.js');

function factory(dependencies) {

    class ThreadPartnerSeenInfo extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
        static _createRecordLocalId(data) {
            const {
                __mfield_channelId,
                __mfield_partnerId,
            } = data;
            return `${this.modelName}_${__mfield_channelId}_${__mfield_partnerId}`;
        }

        /**
         * @private
         * @returns {mail.partner|undefined}
         */
        _computePartner() {
            return [['insert', {
                __mfield_id: this.__mfield_partnerId(this),
            }]];
        }

        /**
         * @private
         * @returns {mail.thread|undefined}
         */
        _computeThread() {
            return [['insert', {
                __mfield_id: this.__mfield_channelId(this),
                __mfield_model: 'mail.channel',
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
        __mfield_channelId: attr(),
        __mfield_lastFetchedMessage: many2one('mail.message'),
        __mfield_lastSeenMessage: many2one('mail.message'),
        /**
         * Partner that this seen info is related to.
         *
         * Should not write on this field to update relation, and instead
         * should write on @see partnerId field.
         */
        __mfield_partner: many2one('mail.partner', {
            compute: '_computePartner',
            dependencies: [
                '__mfield_partnerId',
            ],
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
        __mfield_partnerId: attr(),
        /**
         * Thread (channel) that this seen info is related to.
         *
         * Should not write on this field to update relation, and instead
         * should write on @see channelId field.
         */
        __mfield_thread: many2one('mail.thread', {
            compute: '_computeThread',
            dependencies: [
                '__mfield_channelId',
            ],
            inverse: '__mfield_partnerSeenInfos',
        }),
    };

    return ThreadPartnerSeenInfo;
}

registerNewModel('mail.thread_partner_seen_info', factory);

});
