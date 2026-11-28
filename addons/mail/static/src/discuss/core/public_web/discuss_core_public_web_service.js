import { proxy } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

export class DiscussCorePublicWeb {
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {import("services").ServiceFactories} services
     */
    constructor(env, services) {
        this.env = env;
        this.store = services["mail.store"];
        this.busService = services.bus_service;
<<<<<<< 73ab2ca1845c9cd40a1c5cf0a3f8b793b97c179b
        this.busService.subscribe("discuss.channel/joined", async (payload) => {
            const { store_data, channel_id } = payload;
||||||| b93d8533d2631ccb17eaa47dce4ed26026a4ece9
        this.notificationService = services.notification;
        this.busService.subscribe("discuss.channel/joined", async (payload) => {
            const {
                store_data,
                channel_id,
                invite_to_rtc_call,
                invited_by_user_id: invitedByUserId,
            } = payload;
=======
        this.notificationService = services.notification;
        this.busService.subscribe("discuss.channel/joined", async (payload, { id }) => {
            // Notifications of the new channel sent after this one, such as the join
            // message, must not be missed.
            this.busService.forceUpdateChannels({ fromId: id });
            const {
                store_data,
                channel_id,
                invite_to_rtc_call,
                invited_by_user_id: invitedByUserId,
            } = payload;
>>>>>>> 84fd4f0262b6611de2c6c87fc1d09fd1e1b22efa
            this.store.insert(store_data);
            await this.store.fetchChannel(channel_id);
        });
        browser.navigator.serviceWorker?.addEventListener(
            "message",
            async ({ data: { action, data } }) => {
                if (action === "OPEN_CHANNEL") {
                    const channel = await this.store["discuss.channel"].getOrFetch(data.id);
                    channel?.open({ focus: true });
                    if (!data.joinCall || !channel || this.store.rtc.localChannel?.eq(channel)) {
                        return;
                    }
                    if (this.store.rtc.localChannel) {
                        await this.store.rtc.leaveCall();
                    }
                    this.store.rtc.joinCall(channel);
                } else if (action === "POST_RTC_LOGS") {
                    const logs = data || {};
                    logs.odooInfo = odoo.info;
                    const string = JSON.stringify(logs);
                    const blob = new Blob([string], { type: "application/json" });
                    const downloadLink = document.createElement("a");
                    const now = luxon.DateTime.now().toFormat("yyyy-LL-dd_HH-mm");
                    downloadLink.download = `RtcLogs_${now}.json`;
                    const url = URL.createObjectURL(blob);
                    downloadLink.href = url;
                    downloadLink.click();
                    URL.revokeObjectURL(url);
                }
            }
        );
    }
}

export const discussCorePublicWeb = {
    dependencies: ["bus_service", "discuss.rtc", "mail.store"],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {import("services").ServiceFactories} services
     */
    start(env, services) {
        return proxy(new DiscussCorePublicWeb(env, services));
    },
};

registry.category("services").add("discuss.core.public.web", discussCorePublicWeb);
