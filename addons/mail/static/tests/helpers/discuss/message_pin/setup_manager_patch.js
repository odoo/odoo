/* @odoo-module */

import { messagePinService } from "@mail/discuss/message_pin/message_pin_service";
import { setupManager } from "@mail/../tests/helpers/webclient_setup";
import { patch } from "@web/core/utils/patch";

patch(setupManager, "discuss/message_pin", {
    setupServices() {
        return {
            ...this._super(...arguments),
            "discuss.message.pin": messagePinService,
        };
    },
});
