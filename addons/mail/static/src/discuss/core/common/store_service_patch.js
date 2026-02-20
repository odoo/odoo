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
     * @param {string} param0.name
     * @param {number[]} param0.user_ids
     * @returns {Promise<import("models").DiscussChannel>}
     */
    async createGroupChat({ default_display_mode, name, user_ids }) {
        const { channel } = await this.fetchStoreData(
            "/discuss/create_group",
            { default_display_mode, name, user_ids },
            { readonly: false, requestData: true }
        );
        channel.open({ focus: true });
        return channel;
    },
    /** @param {number} channelId */
    async fetchChannel(channelId) {
        const fetchParam = this.fetchParams.find(([name]) => name === "discuss.channel");
        if (fetchParam) {
            const [, channelIds, dataRequest] = fetchParam;
            channelIds.push(channelId);
            await dataRequest._resultResolvers.promise;
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
        return Object.values(this["discuss.channel"].records)
            .filter(
                (channel) => channel?.channel_type === "chat" && channel.correspondent?.partner_id
            )
            .sort((a, b) => compareDatetime(b.lastInterestDt, a.lastInterestDt) || b.id - a.id)
            .map((channel) => channel.correspondent.partner_id.id);
    },
    /**
     * @param {import("models").ChannelMember} m1
     * @param {import("models").ChannelMember} m2
     */
    sortMembers(m1, m2) {
        return m1.name?.localeCompare(m2.name) || m1.id - m2.id;
    },
    /** @param {number[]} user_ids */
    async startChat(user_ids) {
        user_ids = [...new Set([this.self.id, ...user_ids])];
        if (user_ids.length === 1) {
            const chat = await this.joinChat(user_ids[0], true);
            chat.open({ focus: true, bypassCompact: true });
        } else if (user_ids.length === 2) {
            const user_id = user_ids.find((user_id) => user_id !== this.store.self_user?.id);
            const chat = await this.joinChat(user_id, true);
            chat.open({ focus: true, bypassCompact: true });
        } else {
            await this.createGroupChat({ user_ids });
        }
    },
};

patch(Store.prototype, storeServicePatch);
