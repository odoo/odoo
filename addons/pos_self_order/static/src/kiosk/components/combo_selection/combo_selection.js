/** @odoo-module */

import { Component } from "@odoo/owl";
import { useselfOrder } from "@pos_self_order/kiosk/self_order_kiosk_service";
import { AttributeSelection } from "@pos_self_order/kiosk/components/attribute_selection/attribute_selection";

export class ComboSelection extends Component {
    static template = "pos_self_order.ComboSelection";
    static props = ["combo", "comboState", "next"];
    static components = { AttributeSelection };

    setup() {
        this.selfOrder = useselfOrder();
    }

    productClicked(lineId) {
        const comboLine = this.props.combo.combo_line_ids.find((line) => line.id == lineId);
        const productSelected = this.selfOrder.productByIds[comboLine.product_id[0]];
        this.props.comboState.selectedProduct = productSelected;
        if (productSelected.attributes.length === 0) {
            this.props.next();
        }
    }
}
