import { _t } from '@web/core/l10n/translation';
import { rpc } from '@web/core/network/rpc';
import { registry } from '@web/core/registry';
import { Interaction } from '@web/public/interaction';
import wSaleUtils from '@website_sale/js/website_sale_utils';
import wishlistUtils from '@website_sale/js/wishlist_utils';

export class WishlistButton extends Interaction {
    static selector = '.o_add_wishlist, .o_add_wishlist_dyn';
    dynamicSelectors = {
        ...this.dynamicSelectors,
        _productEl: () => this.el.closest('.js_product'),
    };
    dynamicContent = {
        _root: { 't-on-click': this.locked(this.onClick) },
        _productEl: { 't-on-product_changed': this.onProductChanged },
    };

    /**
     * Add the product to the wishlist, or remove it if it's already in it.
     *
     * @param {Event} ev
     */
    async onClick(ev) {
        const button = ev.currentTarget;
        if (button.dataset.wishId) {
            await this.removeProduct(button);
        } else {
            await this.addProduct(button);
        }
    }

    /**
     * Add a product to the wishlist.
     *
     * @param {HTMLElement} button
     */
    async addProduct(button) {
        let productId = parseInt(button.dataset.productId);
        if (!productId) {
            const productEl = button.closest('.js_product');
            productId = await this.waitFor(rpc('/sale/create_product_variant', {
                product_template_id: parseInt(button.dataset.productTemplateId),
                product_template_attribute_value_ids: productEl
                    ? wSaleUtils.getSelectedAttributeValues(productEl) : [],
            }));
            button.dataset.productId = productId;
        }
        if (!productId || wishlistUtils.getWishlistProductIds().includes(productId)) return;

        const wishId = await this.waitFor(rpc('/shop/wishlist/add', { product_id: productId }));
        wishlistUtils.addWishlistProduct(productId);
        wishlistUtils.updateWishlistNavBar();
        this._setWish(button, wishId);
        const saveForLaterButton = document.querySelector('#wsale_save_for_later_button');
        const addedToWishListAlert = document.querySelector('#wsale_added_to_your_wishlist_alert');
        if (saveForLaterButton) {
            saveForLaterButton.classList.add('d-none');
            addedToWishListAlert.classList.remove('d-none');
        }

        const trackingEl = this.el.closest("[data-product-tracking-info]")
            || document.querySelector("#product_detail[data-product-tracking-info]");
        if (trackingEl) {
            const trackingInfo = JSON.parse(trackingEl.dataset.productTrackingInfo);
            const currency = trackingEl.dataset.productGaCurrency;
            wSaleUtils.dispatchTrackingEvent("add_to_wishlist_event", { trackingInfo, currency });
        }
    }

    /**
     * Remove a product from the wishlist.
     *
     * @param {HTMLElement} button
     */
    async removeProduct(button) {
        await this.waitFor(rpc(`/shop/wishlist/remove/${button.dataset.wishId}`));
        wishlistUtils.removeWishlistProduct(parseInt(button.dataset.productId));
        wishlistUtils.updateWishlistNavBar();
        this._setWish(button, false);
    }

    /**
     * Update the "add to wishlist" button based on the selected variant.
     *
     * @param {CustomEvent} event
     */
    onProductChanged(event) {
        const button = event.currentTarget.querySelector('.o_add_wishlist_dyn');
        if (button) {
            this._setWish(button, event.detail.wishId);
        }
    }

    /**
     * Store or remove the wishlist line of the button's product.
     *
     * @param {HTMLElement} button
     * @param {number|false} wishId The `product.wishlist` id, falsy if not in the wishlist.
     */
    _setWish(button, wishId) {
        if (wishId) {
            button.dataset.wishId = wishId;
        } else {
            delete button.dataset.wishId;
        }
        this._updateButton(button, !!wishId);
    }

    /**
     * Update the button's icon and labels to reflect whether its product is in
     * the wishlist.
     *
     * @param {HTMLElement} button
     * @param {boolean} inWishlist
     */
    _updateButton(button, inWishlist) {
        button.querySelector('.oi')?.classList.toggle('oi-filled', inWishlist);
        const title = inWishlist ? _t("Remove from wishlist") : _t("Add to wishlist");
        button.title = title;
        button.querySelector('.oi[aria-label]')?.setAttribute('aria-label', title);
        const labelEl = button.querySelector('.o_label');
        if (labelEl) {
            labelEl.textContent = inWishlist ? _t("In your wishlist") : _t("Add to wishlist");
        }
    }
}

registry
    .category('public.interactions')
    .add('website_sale.wishlist_button', WishlistButton);
