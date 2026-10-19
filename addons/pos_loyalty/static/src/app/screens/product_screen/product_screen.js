import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { useBarcodeReader } from "@point_of_sale/app/hooks/barcode_reader_hook";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(ProductScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.notification = useService("notification");
        useBarcodeReader({
            coupon: this._onCouponScan.bind(this),
        });
    },
    async _onCouponScan(code) {
        const order = this.pos.getOrder();
        const loadError = await this.pos.loadCode(code.base_code);
        if (loadError) {
            this.notification.add(loadError, { type: "danger" });
            return;
        }
        await this.pos.applyCode(code.base_code);
        order.recomputeRewards();
    },
    async _barcodePartnerAction(code) {
        await super._barcodePartnerAction(code);
        this.pos.updateRewards();
    },
});
