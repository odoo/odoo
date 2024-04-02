import { reactive } from "@odoo/owl";

import { registry } from "@web/core/registry";

export const OTHER_LONG_TYPING = 60000;

export class Typing {
    busService;
    /** @type {import("@mail/core/common/store_service").Store} */
    storeService;

    /**
     * @param {Partial<import("services").Services>} services
     */
    constructor(services) {
        this.busService = services.bus_service;
        this.storeService = services["mail.store"];
    }

    setup() {
        this.busService.subscribe("discuss.channel.member/typing_status", (payload) => {
            const member = this.storeService.ChannelMember.insert(payload);
            member.threadAsTyping = payload.isTyping ? member.thread : undefined;
        });
    }
}

export const discussTypingService = {
    dependencies: ["bus_service", "mail.store"],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    start(env, services) {
        const typing = reactive(new Typing(services));
        typing.setup();
        return typing;
    },
};

registry.category("services").add("discuss.typing", discussTypingService);
