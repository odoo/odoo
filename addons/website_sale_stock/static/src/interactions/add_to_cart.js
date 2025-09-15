import { patch } from '@web/core/utils/patch';
import { AddToCart } from '@website_sale/interactions/add_to_cart';

patch(AddToCart.prototype, {
    /**
     * Override of `website_sale` to recompute the combination info after adding a product to the
     * cart.
     *
     * @param {MouseEvent} ev
     */
    async addToCart(ev) {
        const quantity = await this.waitFor(super.addToCart(...arguments));
        if (document.querySelector('div.availability_messages')) {
            // Trigger an event to recompute the combination info.
            document.querySelectorAll('.o_wsale_product_page_variants').forEach(
                el => el.dispatchEvent(new Event('change'))
            );
        }
        return quantity;
    },
});
