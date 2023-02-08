/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { SaleOrderRow } from "./SaleOrderRow";

/**
 * @props {models.Order} [initHighlightedOrder] initially highligted order
 * @props {Array<models.Order>} orders
 */
export class SaleOrderList extends Component {
    static components = { SaleOrderRow };
    static template = "SaleOrderList";

    setup() {
        super.setup();
        this.state = useState({ highlightedOrder: this.props.initHighlightedOrder || null });
    }
    get highlightedOrder() {
        return this.state.highlightedOrder;
    }
    _onClickOrder(order) {
        this.state.highlightedOrder = order;
    }
}
