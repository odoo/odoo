import { Component, proxy, useProps, usePlugin, t } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";
import { CartPlugin } from "@website_sale/js/cart_plugin";

export const CLICK_DELAY = 200;

export class CartLine extends Component {
    static template = "website_sale.CartLine";
    props = useProps({
        templateData: t.object(),
        line: t.object(),
    });
    cart = usePlugin(CartPlugin);

    setup() {
        this.cartService = useService("cart");
        this.state = proxy({
            quantity: this.props.line.displayed_quantity,
        });
        this.updateQuantityDebounced = useDebounced(() => {
            this.cart.updateLine(
                parseInt(this.props.line.id), // in case of removing consolidated discount lines, the line id can be a string
                this.props.line.product_id,
                this.state.quantity
            );
        }, CLICK_DELAY);
    }

    updateQuantity(quantity) {
        const newQuantity = parseInt(quantity);
        const { min_quantity, max_quantity } = this.props.line;

        if (
            Number.isNaN(newQuantity) ||
            newQuantity === this.state.quantity ||
            // 0 removes the line, which is always allowed.
            (min_quantity && newQuantity !== 0 && newQuantity < min_quantity) ||
            (max_quantity !== null && newQuantity > max_quantity)
        ) {
            return;
        }

        this.state.quantity = newQuantity;
        this.updateQuantityDebounced();
    }

    addToWishlist() {
        this.cart.addToWishlist(this.props.line.id, this.props.line.product_id);
    }
}
