/* @odoo-module */

import { mailCoreCommon } from "@mail/core/common/mail_core_common_service";
import { setupManager } from "@mail/../tests/helpers/webclient_setup";

import { patch } from "@web/core/utils/patch";

patch(setupManager, "mail/core/common", {
    setupServices(...args) {
        return {
            ...this._super(...args),
            "mail.core.common": mailCoreCommon,
        };
    },
});
