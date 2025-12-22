import { Component, useExternalListener, useState } from "@odoo/owl";

export class ProductInfoPopup extends Component {
    static template = "pos_self_order.ProductInfoPopup";
    static props = {
        product: Object,
        addToCart: Function,
        close: Function,
        isComboLine: { type: Boolean, optional: true },
    };

    setup() {
        useExternalListener(window, "click", this.props.close);
        this.state = useState({
            qty: 1,
        });
    }

    addToCartAndClose() {
        this.props.addToCart(this.state.qty);
        this.props.close();
    }

    changeQuantity(increase) {
        const currentQty = this.state.qty;

        if (!increase && currentQty === 1) {
            return;
        }

        return increase ? this.state.qty++ : this.state.qty--;
    }
}
