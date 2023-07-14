/* @odoo-module */

import { reactive } from "@odoo/owl";

import { registry } from "@web/core/registry";

export class DiscussCoreWeb {
    constructor(env, services) {
        Object.assign(this, { env, ui: services.ui });
        /** @type {import("@mail/core/common/chat_window_service").ChatWindowService} */
        this.chatWindowService = services["mail.chat_window"];
        /** @type {import("@mail/core/common/store_service").Store} */
        this.store = services["mail.store"];
    }

    setup() {
        this.env.bus.addEventListener(
            "discuss.channel/new_message",
            ({ detail: { channel, message } }) => {
                if (
                    !this.ui.isSmall &&
                    channel.correspondent !== this.store.odoobot &&
                    !message.isSelfAuthored
                ) {
                    this.chatWindowService.insert({ thread: channel });
                }
            }
        );
    }
}

export const discussCoreWeb = {
    dependencies: ["mail.chat_window", "mail.store", "ui"],
    start(env, services) {
        const discussCoreWeb = reactive(new DiscussCoreWeb(env, services));
        discussCoreWeb.setup();
        return discussCoreWeb;
    },
};

registry.category("services").add("discuss.core.web", discussCoreWeb);
