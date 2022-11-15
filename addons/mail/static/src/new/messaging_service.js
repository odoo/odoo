/** @odoo-module */

import { Messaging, asyncMethods } from "./messaging";

export const messagingService = {
    dependencies: ["rpc", "orm", "user", "router", "bus_service", "im_status", "notification"],
    async: asyncMethods,
    start(env, { rpc, orm, user, router, bus_service: bus, im_status, notification }) {
        // compute initial discuss thread
        let threadId = "inbox";
        const activeId = router.current.hash.active_id;
        if (typeof activeId === "string" && activeId.startsWith("mail.box_")) {
            threadId = activeId.slice(9);
        }
        if (typeof activeId === "string" && activeId.startsWith("mail.channel_")) {
            threadId = parseInt(activeId.slice(13), 10);
        }

        const messaging = new Messaging(
            env,
            rpc,
            orm,
            user,
            router,
            threadId,
            im_status,
            notification
        );
        messaging.initialize();
        bus.addEventListener("notification", (notifEvent) => {
            messaging.handleNotification(notifEvent.detail);
        });

        // debugging. remove this
        window.messaging = messaging;
        return messaging;
    },
};
