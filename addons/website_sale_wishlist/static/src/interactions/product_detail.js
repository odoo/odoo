import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import wishlistUtils from '@website_sale_wishlist/js/website_sale_wishlist_utils';

export class ProductDetail extends Interaction {
    static selector = '#product_detail';
    dynamicContent = {
        '.js_product': { 't-on-product_changed': this.onProductChanged },
    };

    /**
     * Enable/disable the "add to wishlist" button based on the selected variant.
     *
     * @param {CustomEvent} event
     */
    onProductChanged(event) {
        const input = event.target;
        const button = input.closest('.js_product')?.querySelector('[data-action="o_wishlist"]');
        if (button) {
            const { productId } = event.detail;
            const isDisabled = wishlistUtils.getWishlistProductIds().includes(parseInt(productId));
            wishlistUtils.updateDisabled(button, isDisabled);
            button.dataset.productProductId = productId;
        }
    }
}

registry
    .category('public.interactions')
    .add('website_sale_wishlist.product_detail', ProductDetail);
