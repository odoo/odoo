/** @odoo-module */

import { Component } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/self_order_service";
import { AttributeSelection } from "@pos_self_order/app/components/attribute_selection/attribute_selection";

export class ComboSelection extends Component {
    static template = "pos_self_order.ComboSelection";
    static props = ["combo", "comboState", "next"];
    static components = { AttributeSelection };

    setup() {
        this.selfOrder = useSelfOrder();
    }

    productClicked(lineId) {
        // Keep track of the current combo line id.
        // It servers as additional info for each line so that when calculating prices,
        // no need to look for the specific combo line the product belongs to.
        this.env.currentComboLineId.value = lineId;

        const comboLine = this.props.combo.combo_line_ids.find((line) => line.id == lineId);
        const productSelected = this.selfOrder.productByIds[comboLine.product_id[0]];
        if (!productSelected.self_order_available) {
            return;
        }
        this.props.comboState.selectedProduct = productSelected;
        if (productSelected.attributes.length === 0) {
            this.props.next();
            return;
        }
        this.props.comboState.showQtyButtons = true;
    }
}
