import { reactive } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";

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
        this.discussCoreCommonService = services["discuss.core.common"];
        this.store = services["mail.store"];
        try {
            this.sidebarCategoriesBroadcast = new browser.BroadcastChannel(
                "discuss_core_web.sidebar_categories"
            );
        } catch {
            // BroadcastChannel API is not supported (e.g. Safari < 15.4), so disabling it.
        }
    }

    setup() {
        this.sidebarCategoriesBroadcast?.addEventListener("message", ({ data: { id, open } }) => {
            const category = this.store.DiscussAppCategory.get(id);
            if (category) {
                category.open = open;
            }
        });
        this.env.bus.addEventListener(
            "discuss.channel/new_message",
            ({ detail: { channel, message } }) => {
                if (this.ui.isSmall || message.isSelfAuthored) {
                    return;
                }
                if (channel.isCorrespondentOdooBot && this.store.odoobotOnboarding) {
                    // this cancels odoobot onboarding auto-opening of chat window
                    this.store.odoobotOnboarding = false;
                    return;
                }
                channel.notifyMessageToUser(message);
            }
        );
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

    /**
     * Send the state of a category to the other tabs.
     *
     * @param {import("models").DiscussAppCategory} category
     */
    broadcastCategoryState(category) {
        this.sidebarCategoriesBroadcast?.postMessage({ id: category.id, open: category.open });
    }
}

export const discussCoreWeb = {
    dependencies: ["bus_service", "discuss.core.common", "mail.store", "notification", "ui"],
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
