import { Component, onPatched, proxy } from "@odoo/owl";
import { useRef } from "@web/owl2/utils";

export class OrderHistoryLine extends Component {
    static props = { line: Object, focus: Boolean };
    static template = "website_sale.OrderHistoryLine";

    setup() {
        this.state = proxy({ quantity: this.props.line.product_uom_qty });
        this.qtyInput = useRef("qtyInput");

        onPatched(() => {
            if (this.props.focus) {
                this.qtyInput.el.focus();
            }
        });
    }

    parseInt(value) {
        return parseInt(value);
    }

    updateQuantity(quantity) {
        this.state.quantity = quantity;
    }

    async doReorder() {
        if (this.state.quantity <= 0) {
            return;
        }

        return await this.env.handleReorder({
            product_tmpl_id: this.props.line.product_tmpl_id,
            product_id: this.props.line.product_id,
            quantity: this.state.quantity,
            is_combo: this.props.line.is_combo,
            ...(
                this.props.line.is_combo
                && { selected_combo_items: this.props.line.selected_combo_items }
            ),
        });
    }
}
