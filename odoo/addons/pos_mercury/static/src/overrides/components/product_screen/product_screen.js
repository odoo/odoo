/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { useBarcodeReader } from "@point_of_sale/app/barcode/barcode_reader_hook";
import { patch } from "@web/core/utils/patch";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";

patch(ProductScreen.prototype, {
    setup() {
        super.setup(...arguments);
        useBarcodeReader({
            credit: this.credit_error_action,
        });
    },
    credit_error_action() {
        this.popup.add(ErrorPopup, {
            body: _t("Go to payment screen to use cards"),
        });
    },
});
