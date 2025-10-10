import { rpc } from '@web/core/network/rpc';
import { registry } from '@web/core/registry';
import { Interaction } from '@web/public/interaction';
import wSaleUtils from '@website_sale/js/website_sale_utils';
import wishlistUtils from '@website_sale_wishlist/js/website_sale_wishlist_utils';

export class AddToWishlist extends Interaction {
    static selector = '.o_add_wishlist, .o_add_wishlist_dyn';
    dynamicSelectors = {
        ...this.dynamicSelectors,
        _productEl: () => document.querySelector('.js_product'),
    };
    dynamicContent = {
        _root: { 't-on-click': this.addProduct },
        _productEl: { 't-on-product_changed': this.onProductChanged },
    };

    /**
     * Add a product to the wishlist.
     *
     * @param {Event} ev
     */
    async addProduct(ev) {
        const el = ev.currentTarget;
        let productId = parseInt(el.dataset.productProductId);
        if (!productId) {
            const productEl = el.closest('.js_product');
            productId = await this.waitFor(rpc('/sale/create_product_variant', {
                product_template_id: parseInt(el.dataset.productTemplateId),
                product_template_attribute_value_ids: wSaleUtils.getSelectedAttributeValues(productEl),
            }));
        }
        if (!productId || wishlistUtils.getWishlistProductIds().includes(productId)) return;

        await this.waitFor(rpc('/shop/wishlist/add', { product_id: productId }));
        wishlistUtils.addWishlistProduct(productId);
        wishlistUtils.updateWishlistNavBar();
        wishlistUtils.updateDisabled(el, true);
        if (el.classList.contains('o_add_wishlist')) {
            const iconEl = el.querySelector('.fa');
            if (iconEl) {
                iconEl.classList.remove('fa-heart-o');
                iconEl.classList.add('fa-heart');
            }
        }
    }

    /**
     * Update the "add to wishlist" button based on the selected variant.
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
    .add('website_sale_wishlist.add_to_wishlist', AddToWishlist);
