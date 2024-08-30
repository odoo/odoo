/** @odoo-module **/

import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { useBarcodeReader } from "@point_of_sale/app/barcode/barcode_reader_hook";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(ProductScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.notification = useService("notification");
        useBarcodeReader({
            coupon: this._onCouponScan,
        });
    },
    _onCouponScan(code) {
        // IMPROVEMENT: Ability to understand if the scanned code is to be paid or to be redeemed.
        this.currentOrder.activateCode(code.base_code);
    },
    async _barcodeProductAction(code) {
        await super._barcodeProductAction(code);
        this.currentOrder._updateRewards();
    },
    async _barcodeGS1Action(code) {
        await super._barcodeGS1Action(code);
        this.currentOrder._updateRewards();
    },
});
