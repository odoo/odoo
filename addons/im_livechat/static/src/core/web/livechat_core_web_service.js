import { reactive } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class LivechatCoreWeb {
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    constructor(env, services) {
        this.env = env;
        this.store = services["mail.store"];
        this.busService = services.bus_service;
        this.notificationService = services.notification;
        this.busService.subscribe("im_livechat.channel/joined", async (payload) => {
            const { channel, invited_by_user_id: invitedByUserId } = payload;
            const thread = this.store.Thread.insert(channel);
            await thread.fetchLivechatChannelInfo();
            if (invitedByUserId && invitedByUserId !== this.store.self.userId) {
                this.notificationService.add(
                    _t("You have been invited to #%s", thread.displayName),
                    { type: "info" }
                );
            }
        });
        this.busService.subscribe("im_livechat.channel/leave", async (payload) => {
            const { channel } = payload;
            const thread = this.store.Thread.insert(channel);
            await thread.fetchLivechatChannelInfo();
        });
    }
}

export const livechatCoreWeb = {
    dependencies: ["bus_service", "mail.store", "notification"],

    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    start(env, services) {
        return reactive(new LivechatCoreWeb(env, services));
    },
};

registry.category("services").add("livechat.core.web", livechatCoreWeb);
