/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear, replace } from '@mail/model/model_field_command';
import { sprintf } from '@web/core/utils/strings';

registerModel({
    name: 'MessageSeenIndicator',
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
                return clear();
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
                return clear();
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
                return clear();
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
                return clear();
            }
            return replace(otherPartnersThatHaveSeen);
        },
        /**
         * @private
         * @returns {string|FieldCommand} 
         */
        _computeText() {
            if (this.hasEveryoneSeen) {
                return this.env._t("Seen by Everyone");
            }
            if (this.hasSomeoneSeen) {
                const partnersThatHaveSeen = this.partnersThatHaveSeen.map(partner => {
                    if (this.message.originThread) {
                        return this.message.originThread.getMemberName(partner);
                    }
                    return partner.nameOrDisplayName;
                });
                if (partnersThatHaveSeen.length === 1) {
                    return sprintf(
                        this.env._t("Seen by %s"),
                        partnersThatHaveSeen[0]
                    );
                }
                if (partnersThatHaveSeen.length === 2) {
                    return sprintf(
                        this.env._t("Seen by %s and %s"),
                        partnersThatHaveSeen[0],
                        partnersThatHaveSeen[1]
                    );
                }
                return sprintf(
                    this.env._t("Seen by %s, %s and more"),
                    partnersThatHaveSeen[0],
                    partnersThatHaveSeen[1]
                );
            }
            if (this.hasEveryoneFetched) {
                return this.env._t("Received by Everyone");
            }
            if (this.hasSomeoneFetched) {
                const partnersThatHaveFetched = this.partnersThatHaveFetched.map(partner => {
                    if (this.message.originThread) {
                        return this.message.originThread.getMemberName(partner);
                    }
                    return partner.nameOrDisplayName;
                });
                if (partnersThatHaveFetched.length === 1) {
                    return sprintf(
                        this.env._t("Received by %s"),
                        partnersThatHaveFetched[0]
                    );
                }
                if (partnersThatHaveFetched.length === 2) {
                    return sprintf(
                        this.env._t("Received by %s and %s"),
                        partnersThatHaveFetched[0],
                        partnersThatHaveFetched[1]
                    );
                }
                return sprintf(
                    this.env._t("Received by %s, %s and more"),
                    partnersThatHaveFetched[0],
                    partnersThatHaveFetched[1]
                );
            }
            return clear();
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
        message: one('Message', {
            identifying: true,
            readonly: true,
            required: true,
        }),
        partnersThatHaveFetched: many('Partner', {
            compute: '_computePartnersThatHaveFetched',
        }),
        partnersThatHaveSeen: many('Partner', {
            compute: '_computePartnersThatHaveSeen',
        }),
        text: attr({
            compute: '_computeText',
            default: '',
        }),
        /**
         * The thread concerned by this seen indicator.
         */
        thread: one('Thread', {
            identifying: true,
            inverse: 'messageSeenIndicators',
            readonly: true,
            required: true,
        }),
    },
});
