/** @odoo-module */

import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { useBarcodeReader } from "@point_of_sale/app/barcode/barcode_reader_hook";
import { patch } from "@web/core/utils/patch";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";

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
