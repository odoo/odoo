/* @odoo-module */

import { discussCoreWeb } from "@mail/discuss/core/web/discuss_core_web_service";
import { setupManager } from "@mail/../tests/helpers/webclient_setup";

import { patch } from "@web/core/utils/patch";

patch(setupManager, "discuss/core/web", {
    setupServices(...args) {
        return {
            ...this._super(...args),
            "discuss.core.web": discussCoreWeb,
        };
    },
});
