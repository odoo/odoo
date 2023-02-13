/** @odoo-module */

import { ErrorPopup } from "@point_of_sale/js/Popups/ErrorPopup";
import { _lt } from "@web/core/l10n/translation";

export class ErrorBarcodePopup extends ErrorPopup {
    static template = "ErrorBarcodePopup";
    static defaultProps = {
        confirmText: _lt("Ok"),
        cancelText: _lt("Cancel"),
        title: _lt("Error"),
        body: "",
        message: _lt(
            "The Point of Sale could not find any product, customer, employee or action associated with the scanned barcode."
        ),
    };

    get translatedMessage() {
        return this.env._t(this.props.message);
    }
}
