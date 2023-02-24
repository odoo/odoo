/** @odoo-module */

import { WrappedProductNameLines } from "./WrappedProductNameLines";
import { Component, onWillUpdateProps } from "@odoo/owl";

export class OrderReceipt extends Component {
    static components = { WrappedProductNameLines };
    static template = "OrderReceipt";

    setup() {
        super.setup();
        this._receiptEnv = this.props.order.getOrderReceiptEnv();

        onWillUpdateProps((nextProps) => {
            this._receiptEnv = nextProps.order.getOrderReceiptEnv();
        });
    }
    get receipt() {
        return this.receiptEnv.receipt;
    }
    get orderlines() {
        return this.receiptEnv.orderlines;
    }
    get paymentlines() {
        return this.receiptEnv.paymentlines;
    }
    get isTaxIncluded() {
        return Math.abs(this.receipt.subtotal - this.receipt.total_with_tax) <= 0.000001;
    }
    get receiptEnv() {
        return this._receiptEnv;
    }
    get shippingDate() {
        return this.receiptEnv.shippingDate;
    }
    isSimple(line) {
        return (
            line.discount === 0 &&
            line.is_in_unit &&
            line.quantity === 1 &&
            !(line.display_discount_policy == "without_discount" && line.price < line.price_lst)
        );
    }
}
