/** @odoo-module */
import { Component } from "@odoo/owl";

/**
 * @props {models.Order} order
 * @props columns
 * @emits click-order
 */
export class SaleOrderRow extends Component {
    static template = "SaleOrderRow";

    get order() {
        return this.props.order;
    }
    get highlighted() {
        const highlightedOrder = this.props.highlightedOrder;
        return !highlightedOrder
            ? false
            : highlightedOrder.backendId === this.props.order.backendId;
    }

    // Column getters //

    get name() {
        return this.order.name;
    }
    get date() {
        return moment(this.order.date_order).format("YYYY-MM-DD hh:mm A");
    }
    get partner() {
        const partner = this.order.partner_id;
        return partner ? partner[1] : null;
    }
    get total() {
        return this.env.utils.formatCurrency(this.order.amount_total);
    }
    /**
     * Returns true if the order has unpaid amount, but the unpaid amount
     * should not be the same as the total amount.
     * @returns {boolean}
     */
    get showAmountUnpaid() {
        return this.order.amount_total != this.order.amount_unpaid;
    }
    get amountUnpaidRepr() {
        return this.env.utils.formatCurrency(this.order.amount_unpaid);
    }
    get state() {
        const state_mapping = {
            draft: this.env._t("Quotation"),
            sent: this.env._t("Quotation Sent"),
            sale: this.env._t("Sales Order"),
            done: this.env._t("Locked"),
            cancel: this.env._t("Cancelled"),
        };

        return state_mapping[this.order.state];
    }
    get salesman() {
        const salesman = this.order.user_id;
        return salesman ? salesman[1] : null;
    }
}
