/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many2many, many2one } from '@mail/model/model_field';
import { replace, unlinkAll } from '@mail/model/model_field_command';

registerModel({
    name: 'MessageSeenIndicator',
    identifyingFields: ['thread', 'message'],
    modelMethods: {
        /**
         * @param {Thread} [channel] the concerned thread
         */
        recomputeFetchedValues(channel = undefined) {
            const indicatorFindFunction = channel ? localIndicator => localIndicator.thread === channel : undefined;
            const indicators = this.messaging.models['MessageSeenIndicator'].all(indicatorFindFunction);
            for (const indicator of indicators) {
                indicator.update({
                    hasEveryoneFetched: indicator._computeHasEveryoneFetched(),
                    hasSomeoneFetched: indicator._computeHasSomeoneFetched(),
                    partnersThatHaveFetched: indicator._computePartnersThatHaveFetched(),
                });
            }
        },
        /**
         * @param {Thread} [channel] the concerned thread
         */
        recomputeSeenValues(channel = undefined) {
            const indicatorFindFunction = channel ? localIndicator => localIndicator.thread === channel : undefined;
            const indicators = this.messaging.models['MessageSeenIndicator'].all(indicatorFindFunction);
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
        },
    },
    recordMethods: {
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
        },
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
        },
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
        },
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
        },
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
        },
        /**
         * Manually called as not always called when necessary
         *
         * @private
         * @returns {Partner[]}
         * @see computeFetchedValues
         * @see computeSeenValues
         */
        _computePartnersThatHaveFetched() {
            if (!this.message || !this.thread || !this.thread.partnerSeenInfos) {
                return unlinkAll();
            }
            const otherPartnersThatHaveFetched = this.thread.partnerSeenInfos
                .filter(partnerSeenInfo =>
                    /**
                     * Relation may not be set yet immediately
                     * @see ThreadPartnerSeenInfo:partnerId field
                     * FIXME task-2278551
                     */
                    partnerSeenInfo.partner &&
                    partnerSeenInfo.partner !== this.message.author &&
                    partnerSeenInfo.lastFetchedMessage &&
                    partnerSeenInfo.lastFetchedMessage.id >= this.message.id
                )
                .map(partnerSeenInfo => partnerSeenInfo.partner);
            if (otherPartnersThatHaveFetched.length === 0) {
                return unlinkAll();
            }
            return replace(otherPartnersThatHaveFetched);
        },
        /**
         * Manually called as not always called when necessary
         *
         * @private
         * @returns {Partner[]}
         * @see computeSeenValues
         */
        _computePartnersThatHaveSeen() {
            if (!this.message || !this.thread || !this.thread.partnerSeenInfos) {
                return unlinkAll();
            }
            const otherPartnersThatHaveSeen = this.thread.partnerSeenInfos
                .filter(partnerSeenInfo =>
                    /**
                     * Relation may not be set yet immediately
                     * @see ThreadPartnerSeenInfo:partnerId field
                     * FIXME task-2278551
                     */
                    partnerSeenInfo.partner &&
                    partnerSeenInfo.partner !== this.message.author &&
                    partnerSeenInfo.lastSeenMessage &&
                    partnerSeenInfo.lastSeenMessage.id >= this.message.id)
                .map(partnerSeenInfo => partnerSeenInfo.partner);
            if (otherPartnersThatHaveSeen.length === 0) {
                return unlinkAll();
            }
            return replace(otherPartnersThatHaveSeen);
        },
    },
    fields: {
        hasEveryoneFetched: attr({
            compute: '_computeHasEveryoneFetched',
            default: false,
        }),
        hasEveryoneSeen: attr({
            compute: '_computeHasEveryoneSeen',
            default: false,
        }),
        hasSomeoneFetched: attr({
            compute: '_computeHasSomeoneFetched',
            default: false,
        }),
        hasSomeoneSeen: attr({
            compute: '_computeHasSomeoneSeen',
            default: false,
        }),
        id: attr(),
        isMessagePreviousToLastCurrentPartnerMessageSeenByEveryone: attr({
            compute: '_computeIsMessagePreviousToLastCurrentPartnerMessageSeenByEveryone',
            default: false,
        }),
        /**
         * The message concerned by this seen indicator.
         */
        message: many2one('Message', {
            inverse: 'messageSeenIndicators',
            readonly: true,
            required: true,
        }),
        partnersThatHaveFetched: many2many('Partner', {
            compute: '_computePartnersThatHaveFetched',
        }),
        partnersThatHaveSeen: many2many('Partner', {
            compute: '_computePartnersThatHaveSeen',
        }),
        /**
         * The thread concerned by this seen indicator.
         */
        thread: many2one('Thread', {
            inverse: 'messageSeenIndicators',
            readonly: true,
            required: true,
        }),
    },
});
