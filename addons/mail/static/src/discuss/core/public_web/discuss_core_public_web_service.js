import { reactive } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";

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
        this.notificationService = services.notification;
        this.rtcService = services["discuss.rtc"];
        try {
            this.sidebarCategoriesBroadcast = new browser.BroadcastChannel(
                "discuss_core_public_web.sidebar_categories"
            );
            this.sidebarCategoriesBroadcast.addEventListener(
                "message",
                ({ data: { id, open } }) => {
                    const category = this.store.DiscussAppCategory.get(id);
                    if (category) {
                        category.open = open;
                    }
                }
            );
        } catch {
            // BroadcastChannel API is not supported (e.g. Safari < 15.4), so disabling it.
        }
        this.busService.subscribe("discuss.channel/joined", async (payload) => {
            const { data, channel_id, invited_by_user_id: invitedByUserId } = payload;
            this.store.insert(data);
            const thread = this.store.Thread.get({ id: channel_id, model: "discuss.channel" });
            await thread.fetchChannelInfo();
            if (invitedByUserId && invitedByUserId !== this.store.self.userId) {
                this.notificationService.add(
                    _t("You have been invited to #%s", thread.displayName),
                    { type: "info" }
                );
            }
        });
        browser.navigator.serviceWorker?.addEventListener(
            "message",
            async ({ data: { action, data } }) => {
                if (action === "OPEN_CHANNEL") {
                    const channel = await this.store.Thread.getOrFetch({
                        model: "discuss.channel",
                        id: data.id,
                    });
                    channel?.open();
                    if (!data.joinCall || !channel || this.rtcService.state.channel?.eq(channel)) {
                        return;
                    }
                    if (this.rtcService.state.channel) {
                        await this.rtcService.leaveCall();
                    }
                    this.rtcService.joinCall(channel);
                }
            }
        );
    }

    /**
     * Send the state of a category to the other tabs.
     *
     * @param {import("models").DiscussAppCategory} category
     */
    broadcastCategoryState(category) {
        this.sidebarCategoriesBroadcast?.postMessage({ id: category.id, open: category.open });
    }
}

export const discussCorePublicWeb = {
    dependencies: ["bus_service", "discuss.rtc", "mail.store", "notification"],

    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {import("services").ServiceFactories} services
     */
    start(env, services) {
        return reactive(new DiscussCorePublicWeb(env, services));
    },
};

registry.category("services").add("discuss.core.public.web", discussCorePublicWeb);
