/** @odoo-module */

import { Composer } from "@mail/core/common/composer_model";

Object.assign(Composer.prototype, "whatsapp_composer_model", {
    threadExpired: false,
});
