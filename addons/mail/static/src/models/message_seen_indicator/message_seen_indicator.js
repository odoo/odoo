odoo.define('mail/static/src/models/message_seen_indicator/message_seen_indicator.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2many, many2one, one2many } = require('mail/static/src/model/model_field_utils.js');

function factory(dependencies) {

    class MessageSeenIndicator extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @static
         * @param {mail.thread} [channel] the concerned thread
         */
        static recomputeFetchedValues(channel = undefined) {
            const indicatorFindFunction = channel ? localIndicator => localIndicator.__mfield_thread() === channel : undefined;
            const indicators = this.env.models['mail.message_seen_indicator'].all(indicatorFindFunction);
            for (const indicator of indicators) {
                indicator.update({
                    __mfield_hasEveryoneFetched: indicator._computeHasEveryoneFetched(),
                    __mfield_hasSomeoneFetched: indicator._computeHasSomeoneFetched(),
                    __mfield_partnersThatHaveFetched: indicator._computePartnersThatHaveFetched(),
                });
            }
        }

        /**
         * @static
         * @param {mail.thread} [channel] the concerned thread
         */
        static recomputeSeenValues(channel = undefined) {
            const indicatorFindFunction = channel ? localIndicator => localIndicator.__mfield_thread() === channel : undefined;
            const indicators = this.env.models['mail.message_seen_indicator'].all(indicatorFindFunction);
            for (const indicator of indicators) {
                indicator.update({
                    __mfield_hasEveryoneSeen: indicator._computeHasEveryoneSeen(),
                    __mfield_hasSomeoneFetched: indicator._computeHasSomeoneFetched(),
                    __mfield_hasSomeoneSeen: indicator._computeHasSomeoneSeen(),
                    __mfield_isMessagePreviousToLastCurrentPartnerMessageSeenByEveryone:
                        indicator._computeIsMessagePreviousToLastCurrentPartnerMessageSeenByEveryone(),
                    __mfield_partnersThatHaveFetched: indicator._computePartnersThatHaveFetched(),
                    __mfield_partnersThatHaveSeen: indicator._computePartnersThatHaveSeen(),
                });
            }
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
        static _createRecordLocalId(data) {
            const { __mfield_channelId, __mfield_messageId } = data;
            return `${this.modelName}_${__mfield_channelId}_${__mfield_messageId}`;
        }

        /**
         * Manually called as not always called when necessary
         *
         * @private
         * @returns {boolean}
         * @see computeFetchedValues
         * @see computeSeenValues
         */
        _computeHasEveryoneFetched() {
            if (
                !this.__mfield_message(this) ||
                !this.__mfield_thread(this) ||
                !this.__mfield_thread(this).__mfield_partnerSeenInfos(this)
            ) {
                return false;
            }
            const otherPartnerSeenInfosDidNotFetch =
                this.__mfield_thread(this).__mfield_partnerSeenInfos(this).filter(partnerSeenInfo =>
                    partnerSeenInfo.__mfield_partner(this) !== this.__mfield_message(this).__mfield_author(this) &&
                    (
                        !partnerSeenInfo.__mfield_lastFetchedMessage(this) ||
                        partnerSeenInfo.__mfield_lastFetchedMessage(this).__mfield_id(this) < this.__mfield_message(this).__mfield_id(this)
                    )
            );
            return otherPartnerSeenInfosDidNotFetch.length === 0;
        }

        /**
         * Manually called as not always called when necessary
         *
         * @private
         * @returns {boolean}
         * @see computeSeenValues
         */
        _computeHasEveryoneSeen() {
            if (
                !this.__mfield_message(this) ||
                !this.__mfield_thread(this) ||
                !this.__mfield_thread(this).__mfield_partnerSeenInfos(this)
            ) {
                return false;
            }
            const otherPartnerSeenInfosDidNotSee =
                this.__mfield_thread(this).__mfield_partnerSeenInfos(this).filter(partnerSeenInfo =>
                    partnerSeenInfo.__mfield_partner(this) !== this.__mfield_message(this).__mfield_author(this) &&
                    (
                        !partnerSeenInfo.__mfield_lastSeenMessage(this) ||
                        partnerSeenInfo.__mfield_lastSeenMessage(this).__mfield_id(this) < this.__mfield_message(this).__mfield_id(this)
                    )
            );
            return otherPartnerSeenInfosDidNotSee.length === 0;
        }

        /**
         * Manually called as not always called when necessary
         *
         * @private
         * @returns {boolean}
         * @see computeFetchedValues
         * @see computeSeenValues
         */
        _computeHasSomeoneFetched() {
            if (
                !this.__mfield_message(this) ||
                !this.__mfield_thread(this) ||
                !this.__mfield_thread(this).__mfield_partnerSeenInfos(this)
            ) {
                return false;
            }
            const otherPartnerSeenInfosFetched =
                this.__mfield_thread(this).__mfield_partnerSeenInfos(this).filter(partnerSeenInfo =>
                    partnerSeenInfo.__mfield_partner(this) !== this.__mfield_message(this).__mfield_author(this) &&
                    partnerSeenInfo.__mfield_lastFetchedMessage(this) &&
                    partnerSeenInfo.__mfield_lastFetchedMessage(this).__mfield_id(this) >= this.__mfield_message(this).__mfield_id(this)
            );
            return otherPartnerSeenInfosFetched.length > 0;
        }

        /**
         * Manually called as not always called when necessary
         *
         * @private
         * @returns {boolean}
         * @see computeSeenValues
         */
        _computeHasSomeoneSeen() {
            if (
                !this.__mfield_message(this) ||
                !this.__mfield_thread(this) ||
                !this.__mfield_thread(this).__mfield_partnerSeenInfos(this)
            ) {
                return false;
            }
            const otherPartnerSeenInfosSeen =
                this.__mfield_thread(this).__mfield_partnerSeenInfos(this).filter(partnerSeenInfo =>
                    partnerSeenInfo.__mfield_partner(this) !== this.__mfield_message(this).__mfield_author(this) &&
                    partnerSeenInfo.__mfield_lastSeenMessage(this) &&
                    partnerSeenInfo.__mfield_lastSeenMessage(this).__mfield_id(this) >= this.__mfield_message(this).__mfield_id(this)
            );
            return otherPartnerSeenInfosSeen.length > 0;
        }

        /**
         * Manually called as not always called when necessary
         *
         * @private
         * @returns {boolean}
         * @see computeSeenValues
         */
        _computeIsMessagePreviousToLastCurrentPartnerMessageSeenByEveryone() {
            if (
                !this.__mfield_message(this) ||
                !this.__mfield_thread(this) ||
                !this.__mfield_thread(this).__mfield_lastCurrentPartnerMessageSeenByEveryone(this)
            ) {
                return false;
            }
            return this.__mfield_message(this).__mfield_id(this) < this.__mfield_thread(this).__mfield_lastCurrentPartnerMessageSeenByEveryone(this).__mfield_id(this);
        }

        /**
         * Manually called as not always called when necessary
         *
         * @private
         * @returns {mail.partner[]}
         * @see computeFetchedValues
         * @see computeSeenValues
         */
        _computePartnersThatHaveFetched() {
            if (
                !this.__mfield_message(this) ||
                !this.__mfield_thread(this) ||
                !this.__mfield_thread(this).__mfield_partnerSeenInfos(this)
            ) {
                return [['unlink-all']];
            }
            const otherPartnersThatHaveFetched = this.__mfield_thread(this).__mfield_partnerSeenInfos(this)
                .filter(partnerSeenInfo =>
                    /**
                     * Relation may not be set yet immediately
                     * @see mail.thread_partner_seen_info:partnerId field
                     * FIXME task-2278551
                     */
                    partnerSeenInfo.__mfield_partner(this) &&
                    partnerSeenInfo.__mfield_partner(this) !== this.__mfield_message(this).__mfield_author(this) &&
                    partnerSeenInfo.__mfield_lastFetchedMessage(this) &&
                    partnerSeenInfo.__mfield_lastFetchedMessage(this).__mfield_id(this) >= this.__mfield_message(this).__mfield_id(this)
                )
                .map(partnerSeenInfo => partnerSeenInfo.__mfield_partner(this));
            if (otherPartnersThatHaveFetched.length === 0) {
                return [['unlink-all']];
            }
            return [['replace', otherPartnersThatHaveFetched]];
        }

        /**
         * Manually called as not always called when necessary
         *
         * @private
         * @returns {mail.partner[]}
         * @see computeSeenValues
         */
        _computePartnersThatHaveSeen() {
            if (
                !this.__mfield_message(this) ||
                !this.__mfield_thread(this) ||
                !this.__mfield_thread(this).__mfield_partnerSeenInfos(this)
            ) {
                return [['unlink-all']];
            }
            const otherPartnersThatHaveSeen = this.__mfield_thread(this).__mfield_partnerSeenInfos(this)
                .filter(partnerSeenInfo =>
                    /**
                     * Relation may not be set yet immediately
                     * @see mail.thread_partner_seen_info:partnerId field
                     * FIXME task-2278551
                     */
                    partnerSeenInfo.__mfield_partner(this) &&
                    partnerSeenInfo.__mfield_partner(this) !== this.__mfield_message(this).__mfield_author(this) &&
                    partnerSeenInfo.__mfield_lastSeenMessage(this) &&
                    partnerSeenInfo.__mfield_lastSeenMessage(this).__mfield_id(this) >= this.__mfield_message(this).__mfield_id(this))
                .map(partnerSeenInfo => partnerSeenInfo.__mfield_partner(this));
            if (otherPartnersThatHaveSeen.length === 0) {
                return [['unlink-all']];
            }
            return [['replace', otherPartnersThatHaveSeen]];
        }

        /**
         * @private
         * @returns {mail.message}
         */
        _computeMessage() {
            return [['insert', {
                __mfield_id: this.__mfield_messageId(this),
            }]];
        }

        /**
         * @private
         * @returns {mail.thread}
         */
        _computeThread() {
            return [['insert', {
                __mfield_id: this.__mfield_channelId(this),
                __mfield_model: 'mail.channel',
            }]];
        }
    }

    MessageSeenIndicator.modelName = 'mail.message_seen_indicator';

    MessageSeenIndicator.fields = {
        /**
         * The id of the channel this seen indicator is related to.
         *
         * Should write on this field to set relation between the channel and
         * this seen indicator, not on `thread`.
         *
         * Reason for not setting the relation directly is the necessity to
         * uniquely identify a seen indicator based on channel and message from data.
         * Relational data are list of commands, which is problematic to deduce
         * identifying records.
         *
         * TODO: task-2322536 (normalize relational data) & task-2323665
         * (required fields) should improve and let us just use the relational
         * fields.
         */
        __mfield_channelId: attr(),
        __mfield_hasEveryoneFetched: attr({
            compute: '_computeHasEveryoneFetched',
            default: false,
            dependencies: [
                '__mfield_messageAuthor',
                '__mfield_messageId',
                '__mfield_threadPartnerSeenInfos',
            ],
        }),
        __mfield_hasEveryoneSeen: attr({
            compute: '_computeHasEveryoneSeen',
            default: false,
            dependencies: [
                '__mfield_messageAuthor',
                '__mfield_messageId',
                '__mfield_threadPartnerSeenInfos',
            ],
        }),
        __mfield_hasSomeoneFetched: attr({
            compute: '_computeHasSomeoneFetched',
            default: false,
            dependencies: [
                '__mfield_messageAuthor',
                '__mfield_messageId',
                '__mfield_threadPartnerSeenInfos',
            ],
        }),
        __mfield_hasSomeoneSeen: attr({
            compute: '_computeHasSomeoneSeen',
            default: false,
            dependencies: [
                '__mfield_messageAuthor',
                '__mfield_messageId',
                '__mfield_threadPartnerSeenInfos',
            ],
        }),
        __mfield_id: attr(),
        __mfield_isMessagePreviousToLastCurrentPartnerMessageSeenByEveryone: attr({
            compute: '_computeIsMessagePreviousToLastCurrentPartnerMessageSeenByEveryone',
            default: false,
            dependencies: [
                '__mfield_messageId',
                '__mfield_threadLastCurrentPartnerMessageSeenByEveryone',
            ],
        }),
        /**
         * The message concerned by this seen indicator.
         * This is automatically computed based on messageId field.
         * @see messageId
         */
        __mfield_message: many2one('mail.message', {
            compute: '_computeMessage',
            dependencies: [
                '__mfield_messageId',
            ],
        }),
        __mfield_messageAuthor: many2one('mail.partner', {
            related: '__mfield_message.__mfield_author',
        }),
        /**
         * The id of the message this seen indicator is related to.
         *
         * Should write on this field to set relation between the channel and
         * this seen indicator, not on `message`.
         *
         * Reason for not setting the relation directly is the necessity to
         * uniquely identify a seen indicator based on channel and message from data.
         * Relational data are list of commands, which is problematic to deduce
         * identifying records.
         *
         * TODO: task-2322536 (normalize relational data) & task-2323665
         * (required fields) should improve and let us just use the relational
         * fields.
         */
        __mfield_messageId: attr(),
        __mfield_partnersThatHaveFetched: many2many('mail.partner', {
            compute: '_computePartnersThatHaveFetched',
            dependencies: [
                '__mfield_messageAuthor',
                '__mfield_messageId',
                '__mfield_threadPartnerSeenInfos',
            ],
        }),
        __mfield_partnersThatHaveSeen: many2many('mail.partner', {
            compute: '_computePartnersThatHaveSeen',
            dependencies: [
                '__mfield_messageAuthor',
                '__mfield_messageId',
                '__mfield_threadPartnerSeenInfos',
            ],
        }),
        /**
         * The thread concerned by this seen indicator.
         * This is automatically computed based on channelId field.
         * @see channelId
         */
        __mfield_thread: many2one('mail.thread', {
            compute: '_computeThread',
            dependencies: [
                '__mfield_channelId',
            ],
            inverse: '__mfield_messageSeenIndicators'
        }),
        __mfield_threadPartnerSeenInfos: one2many('mail.thread_partner_seen_info', {
            related: '__mfield_thread.__mfield_partnerSeenInfos',
        }),
        __mfield_threadLastCurrentPartnerMessageSeenByEveryone: many2one('mail.message', {
            related: '__mfield_thread.__mfield_lastCurrentPartnerMessageSeenByEveryone',
        }),
    };

    return MessageSeenIndicator;
}

registerNewModel('mail.message_seen_indicator', factory);

});
