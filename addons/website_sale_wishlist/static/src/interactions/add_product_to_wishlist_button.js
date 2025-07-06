import { rpc } from '@web/core/network/rpc';
import { registry } from '@web/core/registry';
import { Interaction } from '@web/public/interaction';
import wSaleUtils from '@website_sale/js/website_sale_utils';
import wishlistUtils from '@website_sale_wishlist/js/website_sale_wishlist_utils';

export class AddProductToWishlistButton extends Interaction {
    static selector = '.o_add_wishlist, .o_add_wishlist_dyn';
    dynamicContent = {
        _root: { 't-on-click': this.addProduct },
    };

    /**
     * Add a product to the wishlist.
     *
     * @param {Event} ev
     */
    async addProduct(ev) {
        const el = ev.currentTarget;
        let productId = parseInt(el.dataset.productProductId);
        const form = el.closest('form');
        if (!productId) {
            productId = await this.waitFor(rpc('/sale/create_product_variant', {
                product_template_id: parseInt(el.dataset.productTemplateId),
                product_template_attribute_value_ids: wSaleUtils.getSelectedAttributeValues(form),
            }));
        }
        if (!productId || wishlistUtils.getWishlistProductIds().includes(productId)) return;

        await this.waitFor(rpc('/shop/wishlist/add', { product_id: productId }));
        wishlistUtils.addWishlistProduct(productId);
        wishlistUtils.updateWishlistNavBar();
        wishlistUtils.updateDisabled(el, true);
        await wSaleUtils.animateClone(
            $(document.querySelector('.o_wsale_my_wish')),
            $(document.querySelector('#product_detail_main') ?? el.closest('.o_cart_product') ?? form),
            25,
            40,
        );
        if (el.classList.contains('o_add_wishlist')) {
            const iconEl = el.querySelector('.fa');
            if (iconEl) {
                iconEl.classList.remove('fa-heart-o');
                iconEl.classList.add('fa-heart');
            }
        }
    }
}

registry
    .category('public.interactions')
    .add('website_sale_wishlist.add_product_to_wishlist_button', AddProductToWishlistButton);
