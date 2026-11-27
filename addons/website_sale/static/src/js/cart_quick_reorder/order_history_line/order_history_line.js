import { Component, onPatched, proxy, signal, t, useProps, usePlugin } from "@odoo/owl";
import { CartPlugin } from "@website_sale/js/cart_plugin";

export class OrderHistoryLine extends Component {
    static template = "website_sale.OrderHistoryLine";
    props = useProps({
        line: t.object(),
        focus: t.boolean(),
    });
    qtyInput = signal.ref();
    cart = usePlugin(CartPlugin);

    setup() {
        this.state = proxy({ quantity: parseInt(this.props.line.product_uom_qty) });

        onPatched(() => {
            if (this.props.focus) {
                this.qtyInput().focus();
            }
        });
    }

    updateQuantity(value) {
        this.state.quantity = parseInt(value) || 0;
    }

    async doReorder() {
        if (this.state.quantity <= 0) {
            return;
        }

        return await this.cart.reorder({
            product_tmpl_id: this.props.line.product_tmpl_id,
            product_id: this.props.line.product_id,
            quantity: this.state.quantity,
            is_combo: this.props.line.is_combo,
            ...(this.props.line.is_combo && {
                selected_combo_items: this.props.line.selected_combo_items,
            }),
        });
    }
}
