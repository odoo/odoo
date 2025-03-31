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

    productClicked(line) {
        // Keep track of the current combo item id.
        // It servers as additional info for each line so that when calculating prices,
        // no need to look for the specific combo item the product belongs to.
        this.env.currentComboItemId.value = line.id;
        const productSelected = line.product_id;
        if (!productSelected.self_order_available) {
            return;
        }

        this.props.comboState.selectedProduct = productSelected;
        if (
            productSelected.attribute_line_ids.length === 0 ||
            productSelected.product_template_variant_value_ids.length !== 0
        ) {
            this.props.next();
            return;
        }
        this.props.comboState.showQtyButtons = true;
    }
}
