// @ts-check
/** @odoo-module native */
import {
    REACHABLE_IM_STATUSES,
    reachableDecoratedImStatuses,
} from "@mail/core/common/presence_status";
import { Store } from "@mail/core/common/store_service";
import { compareDatetime } from "@mail/utils/common/misc";
import { makeLogger } from "@web/core/debug/debug_logger";
import { patch } from "@web/core/utils/patch";
import { debounce } from "@web/core/utils/timing";

const log = makeLogger("mail.store");
/** @type {Partial<import("models").Store> & ThisType<import("models").Store>} */
const storeServicePatch = {
    setup() {
        super.setup();
        /** @type {Map<number, import("@web/core/utils/concurrency").Deferred>} */
        this.channelIdsFetchingDeferred = new Map();
        /** @type {string[]} */
        this.channel_types_with_seen_infos = [];
        this.updateBusSubscription = debounce(
            () => this.env.services.bus_service.forceUpdateChannels(),
            0,
        );
    },
    get onlineMemberStatuses() {
        // Derived, not a literal: a module that decorates `im_status` registers
        // the pair once and every reader of a presence word sees it, rather than
        // each module patching this getter with its own vocabulary.
        return ["bot", ...REACHABLE_IM_STATUSES, ...reachableDecoratedImStatuses()];
    },
    /**
     * @param {Object} param0
     * @param {string} [param0.default_display_mode]
     * @param {number[]} param0.partners_to
     * @param {string} [param0.name]
     * @returns {Promise<import("models").Thread>}
     */
    async createGroupChat({ default_display_mode, partners_to, name }) {
        log.logic("createGroupChat", () => ({
            default_display_mode,
            partners: partners_to?.length,
            named: Boolean(name),
        }));
        const { channel } = await this.fetchStoreData(
            "/discuss/create_group",
            { default_display_mode, partners_to, name },
            { readonly: false, requestData: true },
        );
        await channel.open({ focus: true });
        return channel;
    },
    /** @param {number} channelId */
    async fetchChannel(channelId) {
        log.pipeline("fetchChannel", () => ({ channelId }));
        await this.fetchStoreData("discuss.channel", [channelId], {
            merge: (queuedIds, [id]) =>
                queuedIds.includes(id) ? queuedIds : [...queuedIds, id],
        });
    },
    /** @returns {number[]} */
    getRecentChatPartnerIds() {
        return Object.values(this.Thread.records)
            .filter((thread) => thread.isDirectChat && thread.correspondent?.partner_id)
            .sort(
                (a, b) =>
                    compareDatetime(b.lastInterestDt, a.lastInterestDt) ||
                    Number(b.id) - Number(a.id),
            )
            .map((thread) => thread.correspondent.partner_id.id);
    },
    /**
     * @param {import("models").ChannelMember} m1
     * @param {import("models").ChannelMember} m2
     */
    sortMembers(m1, m2) {
        return (m1.name || "").localeCompare(m2.name || "") || m1.id - m2.id;
    },
    /** @param {number[]} partnerIds */
    async startChat(partnerIds) {
        const partners_to = [...new Set([this.self.id, ...partnerIds])];
        log.logic("startChat", () => ({ partners: partners_to.length }));
        if (partners_to.length === 1) {
            const chat = await this.joinChat(partners_to[0], true);
            chat.open({ focus: true, bypassCompact: true });
        } else if (partners_to.length === 2) {
            const correspondentId = partners_to.find(
                (partnerId) => partnerId !== this.store.self.id,
            );
            const chat = await this.joinChat(correspondentId, true);
            chat.open({ focus: true, bypassCompact: true });
        } else {
            await this.createGroupChat({ partners_to });
        }
    },
};

patch(Store.prototype, storeServicePatch);
