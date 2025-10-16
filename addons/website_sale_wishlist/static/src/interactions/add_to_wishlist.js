import { rpc } from '@web/core/network/rpc';
import { registry } from '@web/core/registry';
import { Interaction } from '@web/public/interaction';
import wSaleUtils from '@website_sale/js/website_sale_utils';
import wishlistUtils from '@website_sale_wishlist/js/website_sale_wishlist_utils';

export class AddToWishlist extends Interaction {
    static selector = '.o_add_wishlist, .o_add_wishlist_dyn';
    dynamicSelectors = {
        ...this.dynamicSelectors,
        _productEl: () => this.el.closest('.js_product'),
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
        const button = ev.currentTarget;
        let productId = parseInt(button.dataset.productId);
        if (!productId) {
            const productEl = button.closest('.js_product');
            productId = await this.waitFor(rpc('/sale/create_product_variant', {
                product_template_id: parseInt(button.dataset.productTemplateId),
                product_template_attribute_value_ids: productEl
                    ? wSaleUtils.getSelectedAttributeValues(productEl) : [],
            }));
        }
        if (!productId || wishlistUtils.getWishlistProductIds().includes(productId)) return;

        await this.waitFor(rpc('/shop/wishlist/add', { product_id: productId }));
        wishlistUtils.addWishlistProduct(productId);
        wishlistUtils.updateWishlistNavBar();
        button.disabled = true;
        if (button.classList.contains('o_add_wishlist')) {
            const iconEl = button.querySelector('.fa');
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
        const button = event.currentTarget.querySelector('.o_add_wishlist_dyn');
        if (button) {
            const { productId } = event.detail;
            button.disabled = wishlistUtils.getWishlistProductIds().includes(parseInt(productId));
            button.dataset.productId = productId;
        }
    }
}

registry
    .category('public.interactions')
    .add('website_sale_wishlist.add_to_wishlist', AddToWishlist);
