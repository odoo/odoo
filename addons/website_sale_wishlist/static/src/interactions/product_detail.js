import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import wishlistUtils from '@website_sale_wishlist/js/website_sale_wishlist_utils';

export class ProductDetail extends Interaction {
    static selector = '#product_detail';
    dynamicContent = {
        'input.product_id': { 't-on-change': this.onChangeVariant },
    };

    /**
     * Enable/disable the "add to wishlist" button based on the selected variant.
     *
     * @param {Event} ev
     */
    onChangeVariant(ev) {
        const input = ev.target;
        const productId = input.value;
        const button = input.closest('.js_product')?.querySelector('[data-action="o_wishlist"]');
        if (button) {
            const isDisabled = wishlistUtils.getWishlistProductIds().includes(parseInt(productId));
            wishlistUtils.updateDisabled(button, isDisabled);
            button.dataset.productProductId = productId;
        }
    }
}

registry
    .category('public.interactions')
    .add('website_sale_wishlist.product_detail', ProductDetail);
