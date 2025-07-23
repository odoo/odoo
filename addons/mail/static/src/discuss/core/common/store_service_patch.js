import { Store } from "@mail/core/common/store_service";
import { compareDatetime } from "@mail/utils/common/misc";

import { patch } from "@web/core/utils/patch";
import { debounce } from "@web/core/utils/timing";

/** @type {import("models").Store} */
const storeServicePatch = {
    /** @override */
    setup() {
        super.setup();
        /** @type {Map<number, Deferred>} */
        this.channelIdsFetchingDeferred = new Map();
        /**
         * Defines channel types that have the message seen indicator/info feature.
         * @see `discuss.channel`._types_allowing_seen_infos()
         *
         * @type {string[]}
         */
        this.channel_types_with_seen_infos = [];
        this.updateBusSubscription = debounce(
            () => this.env.services.bus_service.forceUpdateChannels(),
            0
        );
    },
    get onlineMemberStatuses() {
        return ["away", "bot", "busy", "online"];
    },
    /**
     * @param {Object} param0
     * @param {string} param0.default_display_mode
     * @param {number[]} param0.partners_to
     * @param {string} param0.name
     * @returns {Promise<import("models").Thread>}
     */
    async createGroupChat({ default_display_mode, partners_to, name }) {
        const { channel } = await this.fetchStoreData(
            "/discuss/create_group",
            { default_display_mode, partners_to, name },
            { readonly: false, requestData: true }
        );
        await channel.open({ focus: true });
        return channel;
    },
    /** @param {number} channelId */
    async fetchChannel(channelId) {
        const fetchParam = this.fetchParams.find(([name]) => name === "discuss.channel");
        if (fetchParam) {
            const [, channelIds, dataRequest] = fetchParam;
            channelIds.push(channelId);
            await dataRequest._resultDef;
        } else {
            await this.fetchStoreData("discuss.channel", [channelId]);
        }
    },
    /**
     * List of known partner ids with a direct chat, ordered
     * by most recent interest (1st item being the most recent)
     *
     * @returns {number[]}
     */
    getRecentChatPartnerIds() {
        return Object.values(this.Thread.records)
            .filter((thread) => thread.channel_type === "chat" && thread.correspondent)
            .sort((a, b) => compareDatetime(b.lastInterestDt, a.lastInterestDt) || b.id - a.id)
            .map((thread) => thread.correspondent.partner_id.id);
    },
    /**
     * @param {import("models").ChannelMember} m1
     * @param {import("models").ChannelMember} m2
     */
    sortMembers(m1, m2) {
        return m1.name?.localeCompare(m2.name) || m1.id - m2.id;
    },
    /** @param {number[]} partnerIds */
    async startChat(partnerIds) {
        const partners_to = [...new Set([this.self.id, ...partnerIds])];
        if (partners_to.length === 1) {
            const chat = await this.joinChat(partners_to[0], true);
            chat.open({ focus: true, bypassCompact: true });
        } else if (partners_to.length === 2) {
            const correspondentId = partners_to.find(
                (partnerId) => partnerId !== this.store.self.id
            );
            const chat = await this.joinChat(correspondentId, true);
            chat.open({ focus: true, bypassCompact: true });
        } else {
            await this.createGroupChat({ partners_to });
        }
    },
};

patch(Store.prototype, storeServicePatch);
