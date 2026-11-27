import { Plugin } from "@odoo/owl";
import { formatCurrency } from "@web/core/currency";
import { formatDate } from "@web/core/l10n/dates";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import wishlistUtils from "@website_sale/js/wishlist_utils";

/**
 * Helpers shared by the cart components, built on top of the `cart` service.
 *
 * Provided by each cart component mounted on its own (`providePlugins([CartPlugin])`), then
 * used by it and its children with `usePlugin(CartPlugin)`.
 */
export class CartPlugin extends Plugin {
    cartService = useService("cart");

    /**
     * Format the given price in the currency of the cart.
     *
     * @param {Number} price
     * @returns {String}
     */
    formatPrice(price) {
        return formatCurrency(price, this.cartService.state.currency_id);
    }

    /**
     * Format the given ISO date in the user's locale.
     *
     * @param {String} date - The date, in ISO format.
     * @returns {String}
     */
    formatDate(date) {
        return formatDate(luxon.DateTime.fromISO(date));
    }

    /**
     * Update the quantity of a cart line, from the cart page.
     *
     * @param {Number} lineId - The line's id, as a `sale.order.line` id.
     * @param {Number} productId - The product's id, as a `product.product` id.
     * @param {Number} quantity - The new quantity; 0 removes the line.
     * @returns {Promise<void>}
     */
    async updateLine(lineId, productId, quantity) {
        await this.cartService.update({ lineId, productId, quantity }, { fromCartPage: true });
    }

    /**
     * Move a cart line to the wishlist.
     *
     * @param {Number} lineId - The line's id, as a `sale.order.line` id.
     * @param {Number} productId - The product's id, as a `product.product` id.
     * @returns {Promise<void>}
     */
    async addToWishlist(lineId, productId) {
        await rpc("/shop/wishlist/add", { product_id: productId });
        wishlistUtils.addWishlistProduct(productId);
        wishlistUtils.updateWishlistNavBar();
        await this.updateLine(lineId, productId, 0);
    }

    /**
     * Add a product from the order history back to the cart.
     *
     * @param {Object} lineData
     * @param {Number} lineData.product_tmpl_id - The product template's id.
     * @param {Number} lineData.product_id - The product's id.
     * @param {Number} lineData.quantity - The quantity to add.
     * @param {Boolean} lineData.is_combo - Whether the product is a combo product.
     * @param {Object[]} [lineData.selected_combo_items] - The selected combo items, if any.
     * @returns {Promise<void>}
     */
    async reorder(lineData) {
        const quantity = await this.cartService.add(
            {
                productTemplateId: lineData.product_tmpl_id,
                productId: lineData.product_id,
                isCombo: lineData.is_combo,
                quantity: lineData.quantity,
                ...(lineData.is_combo && { selected_combo_items: lineData.selected_combo_items }),
            },
            {
                isBuyNow: true,
                redirectToCart: false,
                showNotification: false,
                skipOrderAlert: true,
                // The cart summary isn't on the page if the cart was empty.
                renderShorterCartSummary: !this.cartService.state.lines.cart_lines?.length,
            }
        );
        if (quantity) {
            await this.cartService.loadCart({ force: true, withHistory: true });
        }
    }
}
