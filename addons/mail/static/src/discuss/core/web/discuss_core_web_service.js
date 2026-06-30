import { reactive } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class DiscussCoreWeb {
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {import("services").ServiceFactories} services
     */
    constructor(env, services) {
        this.env = env;
        this.busService = services.bus_service;
        this.notificationService = services.notification;
        this.ui = services.ui;
        this.store = services["mail.store"];
        this.multiTab = services.multi_tab;
    }

    setup() {
        this.busService.subscribe("res.users/connection", async ({ partnerId, username }) => {
            // If the current user invited a new user, and the new user is
            // connecting for the first time while the current user is present
            // then open a chat for the current user with the new user.
            const notification = _t("%(user)s just connected for the first time. Wish them luck!", {
                user: username,
            });
            this.notificationService.add(notification, { type: "info" });
            if (!(await this.multiTab.isOnMainTab())) {
                return;
            }
            const chat = await this.store.getChat({ partnerId });
            if (chat && !this.ui.isSmall) {
                chat.openChatWindow({ focus: false });
            }
        });
        this.env.bus.addEventListener("mail.message/delete", ({ detail: { message } }) => {
            if (message.thread?.model === "discuss.channel") {
                // initChannelsUnreadCounter becomes unreliable
                this.store.channels.fetch();
            }
        });
    }
}

export const discussCoreWeb = {
    dependencies: ["bus_service", "mail.store", "notification", "ui", "multi_tab"],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {import("services").ServiceFactories} services
     */
    start(env, services) {
        const discussCoreWeb = reactive(new DiscussCoreWeb(env, services));
        discussCoreWeb.setup();
        return discussCoreWeb;
    },
};

registry.category("services").add("discuss.core.web", discussCoreWeb);
