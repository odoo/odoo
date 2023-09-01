/** @odoo-module */

import { usePos } from "@point_of_sale/app/store/pos_hook";
import { WrappedProductNameLines } from "@point_of_sale/app/screens/receipt_screen/receipt/wrapped_product_name";
import { Component, onWillUpdateProps } from "@odoo/owl";

export class OrderReceipt extends Component {
    static components = { WrappedProductNameLines };
    static template = "point_of_sale.OrderReceipt";

    setup() {
        this.pos = usePos();
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
    /**
     * @param {number} lineId
     * @returns {boolean} true if the line is part of a combo
     */
    lineIsPartOfCombo(lineId) {
        return this.orderlines.find((l) => l.id === lineId || l.cid === lineId).isPartOfCombo();
    }

    /**
     * @param {object} line item of the array given by `this.receiptEnv.orderlines`
     * @returns {object} the corresponding tax objects from `pos.taxes_by_id`
     */
    getOrderlineTaxes(line) {
        return Object.keys(line.tax_details).map((taxId) => this.pos.taxes_by_id[taxId]);
    }

    /**
     * Override this method to customize the tax letter mapping.
     * @param {array} taxes array of tax objects from `pos.taxes_by_id`
     * @returns {string} the tax letter
     */
    getTaxLetter(...taxes) {
        return "";
    }
}
