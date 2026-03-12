import { Component } from "@odoo/owl";
import { useDebounced } from "@web/core/utils/timing";
import { useState } from "@web/owl2/utils";

export const CLICK_DELAY = 200;

export class CartLine extends Component {
    static template = "website_sale.CartLine";
    static props = {
        isQuantityViewActive: Boolean,
        isWishlistViewActive: Boolean,
        isUomFeatureEnabled: Boolean,
        templateData: Object,
        line: Object,
    };

    setup() {
        this.state = useState({
            quantity: this.props.line.displayed_quantity,
        });
        this.updateQuantityDebounced = useDebounced(() => {
            this.env.updateLine(
                parseInt(this.props.line.id),
                this.props.line.product_id,
                this.state.quantity
            );
        }, CLICK_DELAY);
    }

    updateQuantity(quantity) {
        const effectiveQuantity = parseInt(quantity);
        if (
            !Number.isNaN(effectiveQuantity)
            && effectiveQuantity !== this.state.quantity
            && (
                this.props.line.max_qunantity == null
                || effectiveQuantity <= this.props.line.max_qunantity
            )
        ) {
            this.state.quantity = effectiveQuantity;
            this.updateQuantityDebounced();
        }
    }

    addToWishlist() {
        this.env.addToWishlist(parseInt(this.props.line.id), this.props.line.product_id);
    }
}
