/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { usePos } from "@point_of_sale/app/store/pos_hook";

/**
 * @props {models.Order} order
 * @props columns
 * @emits click-order
 */
export class SaleOrderRow extends Component {
    static template = "pos_sale.SaleOrderRow";
    static props = {
        order: Object,
        highlightedOrder: [Object, { value: null }],
        onClickSaleOrder: Function,
    };

    setup() {
        this.pos = usePos();
        this.ui = useState(useService("ui"));
    }
    get order() {
        return this.props.order;
    }
    get highlighted() {
        const highlightedOrder = this.props.highlightedOrder;
        return !highlightedOrder ? false : highlightedOrder.id === this.props.order.id;
    }

    // Column getters //

    get name() {
        return this.order.name;
    }
    get date() {
        return deserializeDateTime(this.order.date_order).toFormat("yyyy-MM-dd HH:mm a");
    }
    get partner() {
        return this.order.partner_id?.name;
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
            draft: _t("Quotation"),
            sent: _t("Quotation Sent"),
            sale: _t("Sales Order"),
            done: _t("Locked"),
            cancel: _t("Cancelled"),
        };

        return state_mapping[this.order.state];
    }
    get salesman() {
        return this.order.user_id?.name;
    }
}
