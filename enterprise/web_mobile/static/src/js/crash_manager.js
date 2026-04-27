/** @odoo-module */

import { registry } from "@web/core/registry";
import mobile from "@web_mobile/js/services/core";

function mobileErrorHandler(env, error, originalError) {
    if (mobile.methods.crashManager) {
        error.originalError = originalError;
        mobile.methods.crashManager(error);
    }
}
registry
    .category("error_handlers")
    .add("web_mobile.errorHandler", mobileErrorHandler, { sequence: 3 });
