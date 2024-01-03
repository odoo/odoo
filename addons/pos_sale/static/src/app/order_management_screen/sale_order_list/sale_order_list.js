/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { SaleOrderRow } from "@pos_sale/app/order_management_screen/sale_order_row/sale_order_row";
import { useService } from "@web/core/utils/hooks";
import { CenteredIcon } from "@point_of_sale/app/generic_components/centered_icon/centered_icon";
import { usePos } from "@point_of_sale/app/store/pos_hook";

/**
 * @props {models.Order} [initHighlightedOrder] initially highligted order
 * @props {Array<models.Order>} orders
 */
export class SaleOrderList extends Component {
    static components = { SaleOrderRow, CenteredIcon };
    static template = "pos_sale.SaleOrderList";
    static props = {
        initHighlightedOrder: [Object, { value: null }],
        orders: Array,
        onClickSaleOrder: Function,
    };

    setup() {
        this.ui = useState(useService("ui"));
        this.pos = usePos();
        this.state = useState({ highlightedOrder: this.props.initHighlightedOrder || null });
    }
    get highlightedOrder() {
        return this.state.highlightedOrder;
    }
}
