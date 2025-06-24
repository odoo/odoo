import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import { rpc } from '@web/core/network/rpc';
import wSaleUtils from '@website_sale/js/website_sale_utils';
import wishlistUtils from '@website_sale_wishlist/js/website_sale_wishlist_utils';

export class AddProductToWishlistButton extends Interaction {
    static selector = '.oe_website_sale';
    dynamicContent = {
        '.o_add_wishlist, .o_add_wishlist_dyn': { 't-on-click': this.addProduct },
        'input.product_id': { 't-on-change': this.onChangeVariant },
    };

    /**
     * Get the products in the wishlist.
     */
    async willStart() {
        const wishCount = parseInt(
            document.querySelector('header#top .my_wish_quantity')?.textContent
        );
        if (wishlistUtils.getWishlistProductIds().length !== wishCount) {
            wishlistUtils.setWishlistProductIds(
                await this.waitFor(rpc('/shop/wishlist/get_product_ids'))
            );
        }
    }

    /**
     * Update the wishlist navbar.
     */
    start() {
        wishlistUtils.updateWishlistNavBar();
    }

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
        this._updateDisabled(el, true);
        await wSaleUtils.animateClone(
            $(document.querySelector('header .o_wsale_my_wish')),
            $(this.el.querySelector('#product_detail_main') ?? form),
            25,
            40,
        );
    }

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
            this._updateDisabled(button, isDisabled);
            button.dataset.productProductId = productId;
        }
    }

    _updateDisabled(el, isDisabled) {
        el.disabled = isDisabled;
        el.classList.toggle('disabled', isDisabled);
    }
}

registry
    .category('public.interactions')
    .add('website_sale_wishlist.add_product_to_wishlist_button', AddProductToWishlistButton);
