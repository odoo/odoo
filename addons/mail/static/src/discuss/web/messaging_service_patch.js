/* @odoo-module */

import { Messaging, messagingService } from "@mail/core/messaging_service";
import { createLocalId } from "@mail/utils/misc";
import { patch } from "@web/core/utils/patch";

patch(Messaging.prototype, "discuss/web", {
    setup(env, services) {
        this._super(...arguments);
        /** @type {import("@mail/core/store_service").Store} */
        this.discussStore = services["discuss.store"];
    },
    /**
     * @override
     */
    async _handleNotificationNewMessage(notif) {
        await this._super(notif);
        const channel =
            this.discussStore.channels[createLocalId("discuss.channel", notif.payload.id)];
        const message = this.store.messages[notif.payload.message.id];
        if (
            !this.ui.isSmall &&
            channel.correspondent !== this.store.odoobot &&
            !message.isSelfAuthored
        ) {
            this.chatWindowService.insert({ thread: channel });
        }
    },
});

patch(messagingService, "discuss/web", {
    dependencies: [...messagingService.dependencies, "discuss.store"],
});
