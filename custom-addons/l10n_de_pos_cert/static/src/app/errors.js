/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";

export class TaxError extends Error {
    constructor(product) {
        super(
            `The tax for the product '${product.display_name}' with id ${product.id} is not allowed.`
        );
    }
}

function taxErrorHandler(env, _error, originalError) {
    if (originalError instanceof TaxError) {
        env.services.popup.add(ErrorPopup, {
            title: _t("Tax Error"),
            body: originalError.message,
        });
        return true;
    }
}

registry.category("error_handlers").add("taxErrorHandler", taxErrorHandler);
