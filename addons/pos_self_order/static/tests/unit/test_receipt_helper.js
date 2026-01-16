import { patch } from "@web/core/utils/patch";
import { TestReceiptUtil } from "@point_of_sale/../tests/unit/test_receipt_helper";

patch(TestReceiptUtil.prototype, {
    get isSelfOrder() {
        const mode = this.store.config.self_ordering_mode;
        return ["mobile", "kiosk"].includes(mode);
    },
    getOrderToPrint() {
        return this.isSelfOrder ? this.store.currentOrder : super.getOrderToPrint();
    },
    async triggerReceiptPrint() {
        if (!this.isSelfOrder) {
            return super.triggerReceiptPrint();
        }
        if (this.type === "order") {
            return this.store.printOrderReceipt(this.order);
        }
        if (this.type === "preparation") {
            return this.store.printKioskChanges(this.order.access_token);
        }
    },
});
