/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class TaxError extends Error {
    constructor(product) {
        super(
            `The tax for the product '${product.display_name}' with id ${product.id} is not allowed.`
        );
    }
}

function taxErrorHandler(env, _error, originalError) {
    if (originalError instanceof TaxError) {
        env.services.dialog.add(AlertDialog, {
            title: _t("Tax Error"),
            body: originalError.message,
        });
        return true;
    }
}

registry.category("error_handlers").add("taxErrorHandler", taxErrorHandler);
