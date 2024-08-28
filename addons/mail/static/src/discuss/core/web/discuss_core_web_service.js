import { reactive } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class DiscussCoreWeb {
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    constructor(env, services) {
        this.env = env;
        this.busService = services.bus_service;
        this.notificationService = services.notification;
        this.ui = services.ui;
        this.store = services["mail.store"];
    }

    setup() {
        this.sidebarCategoriesBroadcast?.addEventListener("message", ({ data: { id, open } }) => {
            const category = this.store.DiscussAppCategory.get(id);
            if (category) {
                category.open = open;
            }
        });
        this.busService.subscribe("discuss.channel/joined", async (payload) => {
            const { channel, invited_by_user_id: invitedByUserId } = payload;
            const thread = this.store.Thread.insert(channel);
            await thread.fetchChannelInfo();
            if (invitedByUserId && invitedByUserId !== this.store.self.userId) {
                this.notificationService.add(
                    _t("You have been invited to #%s", thread.displayName),
                    { type: "info" }
                );
            }
        });
        this.busService.subscribe("res.users/connection", async ({ partnerId, username }) => {
            // If the current user invited a new user, and the new user is
            // connecting for the first time while the current user is present
            // then open a chat for the current user with the new user.
            const notification = _t(
                "%(user)s connected. This is their first connection. Wish them luck.",
                { user: username }
            );
            this.notificationService.add(notification, { type: "info" });
            const chat = await this.store.getChat({ partnerId });
            if (chat && !this.ui.isSmall) {
                this.store.chatHub.opened.add({ thread: chat });
            }
        });
        this.busService.subscribe("discuss.Thread/fold_state", async (data) => {
            const thread = await this.store.Thread.getOrFetch(data);
            if (data.fold_state && thread && data.foldStateCount > thread.foldStateCount) {
                thread.foldStateCount = data.foldStateCount;
                thread.state = data.fold_state;
                if (thread.state === "closed") {
                    const chatWindow = this.store.ChatWindow.get({ thread });
                    chatWindow?.close({ notifyState: false });
                }
            }
        });
        this.env.bus.addEventListener("mail.message/delete", ({ detail: { message } }) => {
            if (message.thread?.model === "discuss.channel") {
                // initChannelsUnreadCounter becomes unreliable
                this.store.channels.fetch();
            }
        });
        this.busService.start();
    }
}

export const discussCoreWeb = {
    dependencies: ["bus_service", "mail.store", "notification", "ui"],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    start(env, services) {
        const discussCoreWeb = reactive(new DiscussCoreWeb(env, services));
        discussCoreWeb.setup();
        return discussCoreWeb;
    },
};

registry.category("services").add("discuss.core.web", discussCoreWeb);
