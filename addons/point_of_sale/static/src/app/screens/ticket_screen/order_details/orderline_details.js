/** @odoo-module */

import { Component } from "@odoo/owl";
import { sprintf } from "@web/core/utils/strings";
import { formatFloat } from "@web/views/fields/formatters";
import { roundPrecision as round_pr } from "@web/core/utils/numbers";
import { usePos } from "@point_of_sale/app/store/pos_hook";

/**
 * @props {pos.order.line} line
 */
export class OrderlineDetails extends Component {
    static template = "point_of_sale.OrderlineDetails";

    setup() {
        this.pos = usePos();
    }
    get line() {
        const line = this.props.line;
        const formatQty = (line) => {
            const quantity = line.get_quantity();
            const unit = line.get_unit();
            const decimals = this.pos.dp["Product Unit of Measure"];
            const rounding = Math.max(unit.rounding, Math.pow(10, -decimals));
            const roundedQuantity = round_pr(quantity, rounding);
            return formatFloat(roundedQuantity, { digits: [69, decimals] });
        };
        return {
            productName: line.get_full_product_name(),
            totalPrice: line.get_price_with_tax(),
            quantity: formatQty(line),
            unit: line.get_unit().name,
            unitPrice: line.get_unit_price(),
        };
    }
    get productName() {
        return this.line.productName;
    }
    get totalPrice() {
        return this.env.utils.formatCurrency(this.line.totalPrice);
    }
    get quantity() {
        return this.line.quantity;
    }
    get unitPrice() {
        return this.env.utils.formatCurrency(this.line.unitPrice);
    }
    get unit() {
        return this.line.unit;
    }
    get pricePerUnit() {
        return ` ${this.unit} at ${this.unitPrice} / ${this.unit}`;
    }
    get customerNote() {
        return this.props.line.get_customer_note();
    }
    getToRefundDetail() {
        return this.pos.toRefundLines[this.props.line.id];
    }
    hasRefundedQty() {
        return !this.pos.isProductQtyZero(this.props.line.refunded_qty);
    }
    getFormattedRefundedQty() {
        return this.env.utils.formatProductQty(this.props.line.refunded_qty);
    }
    hasToRefundQty() {
        const toRefundDetail = this.getToRefundDetail();
        return !this.pos.isProductQtyZero(toRefundDetail && toRefundDetail.qty);
    }
    getFormattedToRefundQty() {
        const toRefundDetail = this.getToRefundDetail();
        return this.env.utils.formatProductQty(toRefundDetail && toRefundDetail.qty);
    }
    getRefundingMessage() {
        return sprintf(this.env._t("Refunding %s in "), this.getFormattedToRefundQty());
    }
    getToRefundMessage() {
        return sprintf(this.env._t("To Refund: %s"), this.getFormattedToRefundQty());
    }
}
