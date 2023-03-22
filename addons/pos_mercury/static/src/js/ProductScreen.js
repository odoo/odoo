/** @odoo-module */

import { ProductScreen } from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import { useBarcodeReader } from "@point_of_sale/app/barcode_reader_hook";
import { patch } from "@web/core/utils/patch";
import { ErrorPopup } from "@point_of_sale/js/Popups/ErrorPopup";

patch(ProductScreen.prototype, "pos_mercury.ProductScreen", {
    setup() {
        this._super(...arguments);
        useBarcodeReader({
            credit: this.credit_error_action,
        });
    },
    credit_error_action() {
        this.popup.add(ErrorPopup, {
            body: this.env._t("Go to payment screen to use cards"),
        });
    },
});
