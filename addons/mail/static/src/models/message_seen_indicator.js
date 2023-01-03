/** @odoo-module **/

import { attr, clear, many, one, Model } from "@mail/model";
import { sprintf } from "@web/core/utils/strings";

Model({
    name: "MessageSeenIndicator",
    fields: {
        hasEveryoneFetched: attr({
            default: false,
            compute() {
                if (!this.message || !this.thread || !this.thread.partnerSeenInfos) {
                    return false;
                }
                const otherPartnerSeenInfosDidNotFetch = this.thread.partnerSeenInfos.filter(
                    (partnerSeenInfo) =>
                        partnerSeenInfo.partner !== this.message.author &&
                        (!partnerSeenInfo.lastFetchedMessage ||
                            partnerSeenInfo.lastFetchedMessage.id < this.message.id)
                );
                return otherPartnerSeenInfosDidNotFetch.length === 0;
            },
        }),
        hasEveryoneSeen: attr({
            default: false,
            compute() {
                if (!this.message || !this.thread || !this.thread.partnerSeenInfos) {
                    return false;
                }
                const otherPartnerSeenInfosDidNotSee = this.thread.partnerSeenInfos.filter(
                    (partnerSeenInfo) =>
                        partnerSeenInfo.partner !== this.message.author &&
                        (!partnerSeenInfo.lastSeenMessage ||
                            partnerSeenInfo.lastSeenMessage.id < this.message.id)
                );
                return otherPartnerSeenInfosDidNotSee.length === 0;
            },
        }),
        hasSomeoneFetched: attr({
            default: false,
            compute() {
                if (!this.message || !this.thread || !this.thread.partnerSeenInfos) {
                    return false;
                }
                const otherPartnerSeenInfosFetched = this.thread.partnerSeenInfos.filter(
                    (partnerSeenInfo) =>
                        partnerSeenInfo.partner !== this.message.author &&
                        partnerSeenInfo.lastFetchedMessage &&
                        partnerSeenInfo.lastFetchedMessage.id >= this.message.id
                );
                return otherPartnerSeenInfosFetched.length > 0;
            },
        }),
        hasSomeoneSeen: attr({
            default: false,
            compute() {
                if (!this.message || !this.thread || !this.thread.partnerSeenInfos) {
                    return false;
                }
                const otherPartnerSeenInfosSeen = this.thread.partnerSeenInfos.filter(
                    (partnerSeenInfo) =>
                        partnerSeenInfo.partner !== this.message.author &&
                        partnerSeenInfo.lastSeenMessage &&
                        partnerSeenInfo.lastSeenMessage.id >= this.message.id
                );
                return otherPartnerSeenInfosSeen.length > 0;
            },
        }),
        id: attr(),
        isMessagePreviousToLastCurrentPartnerMessageSeenByEveryone: attr({
            default: false,
            compute() {
                if (
                    !this.message ||
                    !this.thread ||
                    !this.thread.lastCurrentPartnerMessageSeenByEveryone
                ) {
                    return false;
                }
                return this.message.id < this.thread.lastCurrentPartnerMessageSeenByEveryone.id;
            },
        }),
        /**
         * The message concerned by this seen indicator.
         */
        message: one("Message", { identifying: true }),
        partnersThatHaveFetched: many("Partner", {
            compute() {
                if (!this.message || !this.thread || !this.thread.partnerSeenInfos) {
                    return clear();
                }
                const otherPartnersThatHaveFetched = this.thread.partnerSeenInfos
                    .filter(
                        (partnerSeenInfo) =>
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
                    .map((partnerSeenInfo) => partnerSeenInfo.partner);
                if (otherPartnersThatHaveFetched.length === 0) {
                    return clear();
                }
                return otherPartnersThatHaveFetched;
            },
        }),
        partnersThatHaveSeen: many("Partner", {
            compute() {
                if (!this.message || !this.thread || !this.thread.partnerSeenInfos) {
                    return clear();
                }
                const otherPartnersThatHaveSeen = this.thread.partnerSeenInfos
                    .filter(
                        (partnerSeenInfo) =>
                            /**
                             * Relation may not be set yet immediately
                             * @see ThreadPartnerSeenInfo:partnerId field
                             * FIXME task-2278551
                             */
                            partnerSeenInfo.partner &&
                            partnerSeenInfo.partner !== this.message.author &&
                            partnerSeenInfo.lastSeenMessage &&
                            partnerSeenInfo.lastSeenMessage.id >= this.message.id
                    )
                    .map((partnerSeenInfo) => partnerSeenInfo.partner);
                if (otherPartnersThatHaveSeen.length === 0) {
                    return clear();
                }
                return otherPartnersThatHaveSeen;
            },
        }),
        text: attr({
            default: "",
            compute() {
                if (this.hasEveryoneSeen) {
                    return this.env._t("Seen by Everyone");
                }
                if (this.hasSomeoneSeen) {
                    const partnersThatHaveSeen = this.partnersThatHaveSeen.map((partner) => {
                        if (this.message.originThread) {
                            return this.message.originThread.getMemberName(partner.persona);
                        }
                        return partner.nameOrDisplayName;
                    });
                    if (partnersThatHaveSeen.length === 1) {
                        return sprintf(this.env._t("Seen by %s"), partnersThatHaveSeen[0]);
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
                    const partnersThatHaveFetched = this.partnersThatHaveFetched.map((partner) => {
                        if (this.message.originThread) {
                            return this.message.originThread.getMemberName(partner.persona);
                        }
                        return partner.nameOrDisplayName;
                    });
                    if (partnersThatHaveFetched.length === 1) {
                        return sprintf(this.env._t("Received by %s"), partnersThatHaveFetched[0]);
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
        }),
        /**
         * The thread concerned by this seen indicator.
         */
        thread: one("Thread", { identifying: true, inverse: "messageSeenIndicators" }),
    },
});
