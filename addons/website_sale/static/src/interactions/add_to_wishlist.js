import { rpc } from '@web/core/network/rpc';
import { registry } from '@web/core/registry';
import { Interaction } from '@web/public/interaction';
import wSaleUtils from '@website_sale/js/website_sale_utils';
import wishlistUtils from '@website_sale/js/wishlist_utils';

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
        this._updateButton(true);

        const trackingEl = this.el.closest("[data-product-tracking-info]")
            || document.querySelector("#product_detail[data-product-tracking-info]");
        if (trackingEl) {
            const trackingInfo = JSON.parse(trackingEl.dataset.productTrackingInfo);
            const currency = trackingEl.dataset.productGaCurrency;
            wSaleUtils.dispatchTrackingEvent("add_to_wishlist_event", { trackingInfo, currency });
        }
    }

    /**
     * Update the "add to wishlist" button based on the selected variant.
     *
     * Each button updates itself rather than the first one of the product: the product page
     * shows two of them, the one in the CTA wrapper and the "save for later" one rendered next
     * to the out-of-stock message, and the latter comes first in the DOM.
     *
     * @param {CustomEvent} event
     */
    onProductChanged(event) {
        if (!this.el.classList.contains('o_add_wishlist_dyn')) return;

        const productId = parseInt(event.detail.productId);
        this.el.dataset.productId = productId;
        this._updateButton(wishlistUtils.getWishlistProductIds().includes(productId));
    }

    /**
     * Reflect on the button whether its product is in the wishlist.
     *
     * @param {boolean} isInWishlist
     */
    _updateButton(isInWishlist) {
        this.el.disabled = isInWishlist;
        if (this.el.classList.contains('o_add_wishlist')) {
            this.el.querySelector('.oi')?.classList.toggle('oi-filled', isInWishlist);
        }
        // The "save for later" button isn't shown disabled, it's swapped with an "Added to your
        // wishlist" placeholder
        const wishlistMessageEl = this.el.closest('#stock_wishlist_message');
        if (wishlistMessageEl) {
            this.el.classList.toggle('d-none', isInWishlist);
            wishlistMessageEl.querySelector('#wsale_added_to_your_wishlist_alert')
                ?.classList.toggle('d-none', !isInWishlist);
        }
    }
}

registry
    .category('public.interactions')
    .add('website_sale.add_to_wishlist', AddToWishlist);
