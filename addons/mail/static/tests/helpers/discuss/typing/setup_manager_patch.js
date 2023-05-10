/* @odoo-module */

import { discussTypingService } from "@mail/discuss/typing/typing_service";
import { setupManager } from "@mail/../tests/helpers/webclient_setup";
import { patch } from "@web/core/utils/patch";

patch(setupManager, "discuss/typing", {
    setupServices() {
        return {
            ...this._super(...arguments),
            "discuss.typing": discussTypingService,
        };
    },
});
