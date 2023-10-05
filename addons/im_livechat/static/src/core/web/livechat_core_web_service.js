/* @odoo-module */

import { reactive } from "@odoo/owl";

import { registry } from "@web/core/registry";

export class LivechatCoreWeb {
    constructor(env, services) {
        Object.assign(this, {
            busService: services.bus_service,
        });
        /** @type {import("@mail/core/common/messaging_service").Messaging} */
        this.messagingService = services["mail.messaging"];
        /** @type {import("@mail/core/common/store_service").Store} */
        this.store = services["mail.store"];
    }

    setup() {
        this.messagingService.isReady.then((data) => {
            if (data.current_user_settings?.is_discuss_sidebar_category_livechat_open) {
                this.store.discuss.livechat.isOpen = true;
            }
            this.busService.subscribe("res.users.settings", (payload) => {
                if (payload) {
                    this.store.discuss.livechat.isOpen =
                        payload.is_discuss_sidebar_category_livechat_open ??
                        this.store.discuss.livechat.isOpen;
                }
            });
        });
    }
}

export const livechatCoreWeb = {
    dependencies: ["bus_service", "mail.messaging", "mail.store"],
    start(env, services) {
        const livechatCoreWeb = reactive(new LivechatCoreWeb(env, services));
        livechatCoreWeb.setup();
        return livechatCoreWeb;
    },
};

registry.category("services").add("im_livechat.core.web", livechatCoreWeb);
