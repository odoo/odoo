/* @odoo-module */

import { onChange } from "@mail/utils/misc";
import { reactive } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class DiscussStore {
    /** @type {import("@mail/core/store_service").Store} */
    storeService;
    constructor(env, { "mail.store": storeService }) {
        Object.assign(this, { storeService });
        this.setup(env);
    }

    setup(env) {
        this.env = env;
        this.lastChannelSubscription = "[]";
        this.personas = this.storeService.personas;
    }

    get self() {
        return this.storeService.self;
    }

    /** @type {Object.<string, import("@mail/discuss/channel_model").Channel>} */
    channels = {};
    /** @type {Object.<number, import("@mail/discuss/channel_member_model").ChannelMember>} */
    channelMembers = {};

    /** @type {import("@mail/discuss/rtc/rtc_session_model").rtcSession{}} */
    rtcSessions = {};
    ringingThreads = null;

    async updateBusSubscription() {
        await new Promise(setTimeout); // Wait for thread fully inserted.
        const channelIds = [];
        const ids = Object.keys(this.channels).sort(); // Ensure channels processed in same order.
        for (const id of ids) {
            const channel = this.channels[id];
            if (channel.hasSelfAsMember) {
                channelIds.push(id);
            }
        }
        const channels = JSON.stringify(channelIds);
        if (this.storeService.isMessagingReady && this.lastChannelSubscription !== channels) {
            this.env.services["bus_service"].forceUpdateChannels();
        }
        this.lastChannelSubscription = channels;
    }
}

export const discussStoreService = {
    dependencies: ["mail.store"],
    start(env, services) {
        const res = reactive(new DiscussStore(env, services));
        onChange(res, "channels", () => res.updateBusSubscription());
        return res;
    },
};

registry.category("services").add("discuss.store", discussStoreService);
