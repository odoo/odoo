import { Store } from "@mail/core/common/store_service";
import { fields } from "@mail/model/misc";
import { compareDatetime } from "@mail/utils/common/misc";

import { localeCompare } from "@web/core/l10n/utils";
import { patch } from "@web/core/utils/patch";
import { debounce } from "@web/core/utils/timing";

/** @type {import("models").Store} */
const storeServicePatch = {
    /** @override */
    setup() {
        super.setup();
        /** @type {Map<number, Promise<DiscussChannel|void>>} */
        this.fetchChannelPromiseByChannelId = new Map();
        /**
         * Defines channel types that have the message seen indicator/info feature.
         * @see `discuss.channel`._types_allowing_seen_infos()
         *
         * @type {string[]}
         */
        this.channel_types_with_seen_infos = [];
        // Debounce it to avoid intensive client => worker communication.
        // Should be moved in the bus service at some point.
        this.updateBusSubscription = debounce(
            () => this.env.services.bus_service.forceUpdateChannels(),
            0
        );
        this.favoriteChannels = fields.Many("discuss.channel", {
            inverse: "storeAsFavoriteChannels",
        });
    },
    /**
     * @param {Object} param0
     * @param {string} param0.default_display_mode
     * @param {number[]} param0.users_to
     * @param {string} param0.name
     * @returns {Promise<import("models").DiscussChannel>}
     */
    async createGroupChat({ default_display_mode, users_to, name }) {
        const { channel } = await this.fetchStoreData(
            "/discuss/create_group",
            { default_display_mode, users_to, name },
            { requestData: true }
        );
        channel.open({ focus: true });
        return channel;
    },
    /**
     * @param {number} channelId
     * @param {{ with_last_message?: boolean }} [options]
     */
    async fetchChannel(channelId, { with_last_message = false } = {}) {
        const fetchParam = this.fetchParams.find(([name]) => name === "discuss.channel");
        if (fetchParam) {
            const [, params, dataRequest] = fetchParam;
            params.ids.push(channelId);
            if (with_last_message) {
                params.with_last_message = true;
            }
            await dataRequest._resultResolvers.promise;
        } else {
            await this.fetchStoreData("discuss.channel", {
                ids: [channelId],
                with_last_message: with_last_message,
            });
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
        return localeCompare(m1.name, m2.name) || m1.id - m2.id;
    },
    /** @param {number[]} partnerIds */
    async startChat(partnerIds) {
        const partners_to = [...new Set([this.self.id, ...partnerIds])];
        if (partners_to.length === 1) {
            const chat = await this.joinChat(partners_to[0], true);
            chat.open({ focus: true, bypassCompact: true });
        } else if (partners_to.length === 2) {
            const correspondentId = partners_to.find(
                (partnerId) => partnerId !== this.store.self_user?.partner_id?.id
            );
            const chat = await this.joinChat(correspondentId, true);
            chat.open({ focus: true, bypassCompact: true });
        } else {
            const users_to = [
                ...new Set([
                    this.self_user.id,
                    ...partnerIds
                        .map((partnerId) => this["res.partner"].get(partnerId)?.main_user_id?.id)
                        .filter(Boolean),
                ]),
            ];
            await this.createGroupChat({ users_to });
        }
    },
};

patch(Store.prototype, storeServicePatch);
