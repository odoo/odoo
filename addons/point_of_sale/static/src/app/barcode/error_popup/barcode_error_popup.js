/** @odoo-module */

import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { _t } from "@web/core/l10n/translation";

export class ErrorBarcodePopup extends ErrorPopup {
    static template = "point_of_sale.ErrorBarcodePopup";
    static defaultProps = {
        confirmText: _t("Ok"),
        cancelText: _t("Cancel"),
        title: _t("Error"),
        body: "",
        message: _t(
            "The Point of Sale could not find any product, customer, employee or action associated with the scanned barcode."
        ),
    };

    get translatedMessage() {
        return _t(this.props.message);
    }
}
