// @ts-check
/** @odoo-module native */
import { fields } from "@mail/core/common/record";
import { Store } from "@mail/core/common/store_service";
import { compareDatetime } from "@mail/utils/common/misc";
import { makeLogger } from "@web/core/debug/debug_logger";
import { patch } from "@web/core/utils/patch";

const log = makeLogger("mail.store");
/** @type {Partial<import("models").Store> & ThisType<import("models").Store>} */
const StorePatch = {
    setup() {
        super.setup();
        this.initChannelsUnreadCounter = 0;
        this.counterChannels = fields.Many("Thread", {
            inverse: "storeAsCounterChannel",
        });
    },
    computeGlobalCounter() {
        if (!this.Thread) {
            return super.computeGlobalCounter();
        }
        const channelsFetched = this.channels.status === "fetched";
        let channelsContribution = channelsFetched ? 0 : this.initChannelsUnreadCounter;
        let channelsNeedactionCounter = 0;
        for (const thread of this.counterChannels) {
            if (channelsFetched && thread.displayToSelf && !thread.isMuted) {
                channelsContribution++;
            }
            channelsNeedactionCounter += thread.message_needaction_counter;
        }
        return (
            super.computeGlobalCounter() +
            channelsContribution -
            channelsNeedactionCounter
        );
    },
    /** @returns {import("models").Thread[]} */
    getSelfImportantChannels() {
        return this.getSelfRecentChannels().filter(
            (channel) => channel.importantCounter > 0,
        );
    },
    /** @returns {import("models").Thread[]} */
    getSelfRecentChannels() {
        return Object.values(this.Thread.records)
            .filter((thread) => thread.isChannelKind && thread.self_member_id)
            .sort(
                (a, b) =>
                    compareDatetime(b.lastInterestDt, a.lastInterestDt) ||
                    Number(b.id) - Number(a.id),
            );
    },
    onStarted() {
        super.onStarted();
        if (this.discuss.isActive) {
            log.logic("discuss active at start: fetch channels");
            this.channels.fetch();
        }
    },
};
patch(Store.prototype, StorePatch);
