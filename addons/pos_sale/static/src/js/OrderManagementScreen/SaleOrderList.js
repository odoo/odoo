/** @odoo-module */

import { useListener } from "@web/core/utils/hooks";
import { PosComponent } from "@point_of_sale/js/PosComponent";

import { SaleOrderRow } from "./SaleOrderRow";

const { useState } = owl;

/**
 * @props {models.Order} [initHighlightedOrder] initially highligted order
 * @props {Array<models.Order>} orders
 */
export class SaleOrderList extends PosComponent {
    static components = { SaleOrderRow };
    static template = "SaleOrderList";

    setup() {
        super.setup();
        useListener("click-order", this._onClickOrder);
        this.state = useState({ highlightedOrder: this.props.initHighlightedOrder || null });
    }
    get highlightedOrder() {
        return this.state.highlightedOrder;
    }
    _onClickOrder({ detail: order }) {
        this.state.highlightedOrder = order;
    }
}
