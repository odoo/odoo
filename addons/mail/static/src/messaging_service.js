/** @odoo-module */

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { Messaging } from "./messaging";
import { reactive } from "@odoo/owl";

export const messagingService = {
    dependencies: ["rpc", "orm", "user", "router", "bus_service"],
    start(env, { rpc, orm, user, router, bus_service: bus }) {
        // compute initial discuss thread
        let threadId = "inbox";
        const activeId = router.current.hash.active_id;
        if (typeof activeId === 'string' && activeId.startsWith("mail.box_")) {
            threadId = activeId.slice(9);
        }
        if (typeof activeId === 'string' && activeId.startsWith("mail.channel_")) {
            threadId = parseInt(activeId.slice(13), 10);
        }

        const messaging = reactive(new Messaging(env, rpc, orm, user, router, threadId));
        messaging.initialize();
        bus.addEventListener("notification", (notifEvent) => {
            messaging.handleNotification(notifEvent.detail);
        });

        // debugging. remove this
        window.messaging = messaging;
        return messaging;
    },
};

registry.category("services").add("mail.messaging", messagingService);
