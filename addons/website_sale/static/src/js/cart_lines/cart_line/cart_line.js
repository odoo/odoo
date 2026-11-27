import { Component, proxy, useProps, t } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";

export const CLICK_DELAY = 200;

export class CartLine extends Component {
    static template = "website_sale.CartLine";
    props = useProps({
        templateData: t.object(),
        line: t.object(),
    });

    setup() {
        this.cartService = useService("cart");
        this.state = proxy({
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
                this.props.line.max_quantity === undefined
                || effectiveQuantity <= this.props.line.max_quantity
            )
            && (
                !this.props.line.min_quantity
                || effectiveQuantity >= this.props.line.min_quantity
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
