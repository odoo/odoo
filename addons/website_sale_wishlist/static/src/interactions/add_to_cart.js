import { patch } from '@web/core/utils/patch';
import { AddToCart } from '@website_sale/interactions/add_to_cart';

patch(AddToCart.prototype, {
    /**
     * Override of `website_sale` to remove the added product from the wishlist.
     *
     * @param {MouseEvent} ev
     */
    async addToCart(ev) {
        const quantity = await this.waitFor(super.addToCart(...arguments));
        const button = ev.currentTarget;
        const wishlistPage = button.closest('.o_wsale_wishlist_page');
        if (wishlistPage && quantity > 0) {
            // Trigger removal of the product from the wishlist.
            button.dispatchEvent(new CustomEvent('remove_wish', { 'detail': { goToCart: true }}));
        }
        return quantity;
    },
});
