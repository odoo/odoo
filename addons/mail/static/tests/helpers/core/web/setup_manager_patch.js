/* @odoo-module */

import { mailCoreWeb } from "@mail/core/web/mail_core_web_service";
import { setupManager } from "@mail/../tests/helpers/webclient_setup";

import { patch } from "@web/core/utils/patch";

patch(setupManager, "mail/core/web", {
    setupServices(...args) {
        return {
            ...this._super(...args),
            "mail.core.web": mailCoreWeb,
        };
    },
});
