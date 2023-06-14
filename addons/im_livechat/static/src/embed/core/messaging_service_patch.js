/* @odoo-module */

import { Messaging, initializeMessaging } from "@mail/core/common/messaging_service";
import { insertPersona } from "@mail/core/common/persona_service";
import { patchFn } from "@mail/utils/common/patch";

import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";

let store;

patchFn(initializeMessaging, function () {
    if (session.livechatData?.options.current_partner_id) {
        store.user = insertPersona({
            type: "partner",
            id: session.livechatData.options.current_partner_id,
        });
    }
    store.isMessagingReady = true;
    store.messagingReadyProm.resolve();
});

patch(Messaging.prototype, {
    setup(env, services) {
        this._super(...arguments);
        store = services["mail.store"];
    },
});
