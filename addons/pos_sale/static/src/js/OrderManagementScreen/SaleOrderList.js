/** @odoo-module */

import { useListener } from "@web/core/utils/hooks";
import { LegacyComponent } from "@web/legacy/legacy_component";

import { SaleOrderRow } from "./SaleOrderRow";

const { useState } = owl;

/**
 * @props {models.Order} [initHighlightedOrder] initially highligted order
 * @props {Array<models.Order>} orders
 */
export class SaleOrderList extends LegacyComponent {
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
