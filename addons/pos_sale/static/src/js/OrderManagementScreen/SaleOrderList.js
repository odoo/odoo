/** @odoo-module */

import { useListener } from "@web/core/utils/hooks";
import PosComponent from "@point_of_sale/js/PosComponent";
import Registries from "@point_of_sale/js/Registries";

const { useState } = owl;

/**
 * @props {models.Order} [initHighlightedOrder] initially highligted order
 * @props {Array<models.Order>} orders
 */
class SaleOrderList extends PosComponent {
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
SaleOrderList.template = "SaleOrderList";

Registries.Component.add(SaleOrderList);

export default SaleOrderList;
