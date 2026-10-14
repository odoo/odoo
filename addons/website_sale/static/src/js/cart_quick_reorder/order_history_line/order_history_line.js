import { Component, onPatched, proxy, signal, t, useProps } from "@odoo/owl";

export class OrderHistoryLine extends Component {
    static template = "website_sale.OrderHistoryLine";
    props = useProps({
        line: t.object(),
        focus: t.boolean(),
    });
    qtyInput = signal.ref();

    setup() {
        this.state = proxy({ quantity: this.props.line.product_uom_qty });

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
