odoo.define('mail/static/src/models/message_seen_indicator/message_seen_indicator.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2many, many2one, one2many } = require('mail/static/src/model/model_field.js');

function factory(dependencies) {

    class MessageSeenIndicator extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @static
         * @param {mail.message|integer} message
         * @param {mail.thread|integer} thread
         * @returns {string|undefined}
         */
        static computeId(message, thread) {
            if (message && thread) {
                const messageId = Number.isInteger(message) ? message : message.id;
                const threadId = Number.isInteger(thread) ? thread : thread.id;
                return [messageId, threadId].join('-');
            }
            return undefined;
        }

        /**
         * @static
         * @param {mail.thread} [channel] the concerned thread
         */
        static recomputeFetchedValues(channel = undefined) {
            const indicatorFindFunction = channel ? localIndicator => localIndicator.thread === channel : undefined;
            const indicators = this.env.models['mail.message_seen_indicator'].all(indicatorFindFunction);
            for (const indicator of indicators) {
                indicator.update({
                    hasEveryoneFetched: indicator._computeHasEveryoneFetched(),
                    hasSomeoneFetched: indicator._computeHasSomeoneFetched(),
                    partnersThatHaveFetched: indicator._computePartnersThatHaveFetched(),
                });
            }
        }

        /**
         * @static
         * @param {mail.thread} [channel] the concerned thread
         */
        static recomputeSeenValues(channel = undefined) {
            const indicatorFindFunction = channel ? localIndicator => localIndicator.thread === channel : undefined;
            const indicators = this.env.models['mail.message_seen_indicator'].all(indicatorFindFunction);
            for (const indicator of indicators) {
                indicator.update({
                    hasEveryoneSeen: indicator._computeHasEveryoneSeen(),
                    hasSomeoneFetched: indicator._computeHasSomeoneFetched(),
                    hasSomeoneSeen: indicator._computeHasSomeoneSeen(),
                    isMessagePreviousToLastCurrentPartnerMessageSeenByEveryone:
                        indicator._computeIsMessagePreviousToLastCurrentPartnerMessageSeenByEveryone(),
                    partnersThatHaveFetched: indicator._computePartnersThatHaveFetched(),
                    partnersThatHaveSeen: indicator._computePartnersThatHaveSeen(),
                });
            }
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * Manually called as not always called when necessary
         *
         * @private
         * @returns {boolean}
         * @see computeFetchedValues
         * @see computeSeenValues
         */
        _computeHasEveryoneFetched() {
            if (!this.message || !this.thread || !this.thread.partnerSeenInfos) {
                return false;
            }
            const otherPartnerSeenInfosDidNotFetch =
                this.thread.partnerSeenInfos.filter(partnerSeenInfo =>
                    partnerSeenInfo.partner !== this.message.author &&
                    (
                        !partnerSeenInfo.lastFetchedMessage ||
                        partnerSeenInfo.lastFetchedMessage.id < this.message.id
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
            if (!this.message || !this.thread || !this.thread.partnerSeenInfos) {
                return false;
            }
            const otherPartnerSeenInfosDidNotSee =
                this.thread.partnerSeenInfos.filter(partnerSeenInfo =>
                    partnerSeenInfo.partner !== this.message.author &&
                    (
                        !partnerSeenInfo.lastSeenMessage ||
                        partnerSeenInfo.lastSeenMessage.id < this.message.id
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
            if (!this.message || !this.thread || !this.thread.partnerSeenInfos) {
                return false;
            }
            const otherPartnerSeenInfosFetched =
                this.thread.partnerSeenInfos.filter(partnerSeenInfo =>
                    partnerSeenInfo.partner !== this.message.author &&
                    partnerSeenInfo.lastFetchedMessage &&
                    partnerSeenInfo.lastFetchedMessage.id >= this.message.id
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
            if (!this.message || !this.thread || !this.thread.partnerSeenInfos) {
                return false;
            }
            const otherPartnerSeenInfosSeen =
                this.thread.partnerSeenInfos.filter(partnerSeenInfo =>
                    partnerSeenInfo.partner !== this.message.author &&
                    partnerSeenInfo.lastSeenMessage &&
                    partnerSeenInfo.lastSeenMessage.id >= this.message.id
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
                !this.message ||
                !this.thread ||
                !this.thread.lastCurrentPartnerMessageSeenByEveryone
            ) {
                return false;
            }
            return this.message.id < this.thread.lastCurrentPartnerMessageSeenByEveryone.id;
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
            if (!this.message || !this.thread || !this.thread.partnerSeenInfos) {
                return [['unlink-all']];
            }
            const otherPartnersThatHaveFetched = this.thread.partnerSeenInfos
                .filter(partnerSeenInfo =>
                    partnerSeenInfo.partner !== this.message.author &&
                    partnerSeenInfo.lastFetchedMessage &&
                    partnerSeenInfo.lastFetchedMessage.id >= this.message.id
                )
                .map(partnerSeenInfo => partnerSeenInfo.partner);
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
            if (!this.message || !this.thread || !this.thread.partnerSeenInfos) {
                return [['unlink-all']];
            }
            const otherPartnersThatHaveSeen = this.thread.partnerSeenInfos
                .filter(partnerSeenInfo =>
                    partnerSeenInfo.partner !== this.message.author &&
                    partnerSeenInfo.lastSeenMessage &&
                    partnerSeenInfo.lastSeenMessage.id >= this.message.id)
                .map(partnerSeenInfo => partnerSeenInfo.partner);
            if (otherPartnersThatHaveSeen.length === 0) {
                return [['unlink-all']];
            }
            return [['replace', otherPartnersThatHaveSeen]];
        }
    }

    MessageSeenIndicator.modelName = 'mail.message_seen_indicator';

    MessageSeenIndicator.fields = {
        hasEveryoneFetched: attr({
            compute: '_computeHasEveryoneFetched',
            default: false,
            dependencies: ['messageAuthor', 'messageId', 'threadPartnerSeenInfos'],
        }),
        hasEveryoneSeen: attr({
            compute: '_computeHasEveryoneSeen',
            default: false,
            dependencies: ['messageAuthor', 'messageId', 'threadPartnerSeenInfos'],
        }),
        hasSomeoneFetched: attr({
            compute: '_computeHasSomeoneFetched',
            default: false,
            dependencies: ['messageAuthor', 'messageId', 'threadPartnerSeenInfos'],
        }),
        hasSomeoneSeen: attr({
            compute: '_computeHasSomeoneSeen',
            default: false,
            dependencies: ['messageAuthor', 'messageId', 'threadPartnerSeenInfos'],
        }),
        id: attr(),
        isMessagePreviousToLastCurrentPartnerMessageSeenByEveryone: attr({
            compute: '_computeIsMessagePreviousToLastCurrentPartnerMessageSeenByEveryone',
            default: false,
            dependencies: [
                'messageId',
                'threadLastCurrentPartnerMessageSeenByEveryone',
            ],
        }),
        message: many2one('mail.message'),
        messageAuthor: many2one('mail.partner', {
            related: 'message.author',
        }),
        messageId: attr({
            related: 'message.id',
        }),
        partnersThatHaveFetched: many2many('mail.partner', {
            compute: '_computePartnersThatHaveFetched',
            dependencies: ['messageAuthor', 'messageId', 'threadPartnerSeenInfos'],
        }),
        partnersThatHaveSeen: many2many('mail.partner', {
            compute: '_computePartnersThatHaveSeen',
            dependencies: ['messageAuthor', 'messageId', 'threadPartnerSeenInfos'],
        }),
        thread: many2one('mail.thread', {
            inverse: 'messageSeenIndicators'
        }),
        threadPartnerSeenInfos: one2many('mail.thread_partner_seen_info', {
            related: 'thread.partnerSeenInfos',
        }),
        threadLastCurrentPartnerMessageSeenByEveryone: many2one('mail.message', {
            related: 'thread.lastCurrentPartnerMessageSeenByEveryone',
        }),
    };

    return MessageSeenIndicator;
}

registerNewModel('mail.message_seen_indicator', factory);

});
