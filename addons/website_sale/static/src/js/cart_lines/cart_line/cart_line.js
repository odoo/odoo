import { Component, proxy, props, t } from "@odoo/owl";
import { useDebounced } from "@web/core/utils/timing";

export const CLICK_DELAY = 200;

export class CartLine extends Component {
    static template = "website_sale.CartLine";
    props = props({
        isQuantityViewActive: t.boolean(),
        isWishlistViewActive: t.boolean(),
        isUomFeatureEnabled: t.boolean(),
        templateData: t.object(),
        line: t.object(),
    });

    setup() {
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
                this.props.line.max_qunantity === undefined
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
