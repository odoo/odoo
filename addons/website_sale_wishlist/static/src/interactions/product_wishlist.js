import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import { rpc, RPCError } from '@web/core/network/rpc';
import wSaleUtils from '@website_sale/js/website_sale_utils';

export class ProductWishlist extends Interaction {
    static selector = '.oe_website_sale';
    dynamicContent = {
        '.o_wsale_my_wish': { 't-on-click': this.onClickMyWish },
        '.o_add_wishlist, .o_add_wishlist_dyn': { 't-on-click': this.onClickAddWish },
        'input.product_id': { 't-on-change': this.onChangeVariant },
        'input.js_product_change': { 't-on-change': this.onChangeProduct },
        '.wishlist-section .o_wish_rm': { 't-on-click': this.onClickWishRemove },
        '.wishlist-section .o_wish_add': { 't-on-click': this.onClickWishAdd },
    };

    setup() {
        this.wishlistProductIds = JSON.parse(
            sessionStorage.getItem('website_sale_wishlist_product_ids') || '[]'
        );
    }

    /**
     * Gets the current wishlist items.
     */
    async willStart() {
        const wishCount = parseInt(
            this.el.querySelector('header#top .my_wish_quantity')?.textContent
        );
        if (this.wishlistProductIds.length !== wishCount) {
            const result = await this.waitFor(rpc('/shop/wishlist', { count: 1 }));
            this.wishlistProductIds = JSON.parse(result);
            sessionStorage.setItem('website_sale_wishlist_product_ids', result);
        }
    }

    /**
     * Updates the wishlist view (navbar) & the wishlist button (product page).
     */
    start() {
        this._updateWishlistView();
        // trigger change on only one input
        if (this.el.querySelector('input.js_product_change')) { // handle list view of variants
            this.el.querySelector('input.js_product_change:checked').dispatchEvent(
                new Event('change', { bubbles: true })
            );
        } else {
            this.el.querySelector('input.product_id').dispatchEvent(
                new Event('change', { bubbles: true })
            );
        }
    }

    onClickMyWish() {
        if (this.wishlistProductIds.length === 0) {
            this._updateWishlistView();
            this._redirectNoWish();
            return;
        }
        window.location = '/shop/wishlist';
    }

    onClickAddWish(ev) {
        this._addProduct(ev.currentTarget);
    }

    onChangeVariant(ev) {
        const input = ev.target;
        const productId = input.value;
        const button = input.closest('.js_product').querySelector('[data-action="o_wishlist"]');
        this._updateWishlistButton(button, productId);
    }

    onChangeProduct(ev) {
        const productId = ev.currentTarget.value;
        const button = ev.target.closest('.js_add_cart_variants').querySelector(
            '[data-action="o_wishlist"]'
        );
        this._updateWishlistButton(button, productId);
    }

    onClickWishRemove(ev) {
        this._removeWish(ev, false);
    }

    onClickWishAdd(ev) {
        if (ev.currentTarget.classList.contains('disabled')) {
            ev.preventDefault();
            return;
        }
        this._addOrMoveWish(ev);
    }

    async _addProduct(el) {
        let productId = this._getProductId(el);
        const form = el.closest('form');
        let templateId = form.querySelector('.product_template_id').value;
        // when adding from /shop instead of the product page, need another selector
        if (!templateId) {
            templateId = el.dataset.productTemplateId;
        }
        this._updateDisabled(el, true);

        try {
            if (!productId) {
                productId = await this.waitFor(rpc('/sale/create_product_variant', {
                    product_template_id: templateId,
                    product_template_attribute_value_ids:
                        wSaleUtils.getSelectedAttributeValues(form),
                }));
            }
        } catch (e) {
            this._updateDisabled(el, false);
            if (!(e instanceof RPCError)) throw e;
            return;
        }

        if (productId && !this.wishlistProductIds.includes(productId)) {
            try {
                await this.waitFor(rpc('/shop/wishlist/add', { product_id: productId }));
            } catch (e) {
                this._updateDisabled(el, false);
                if (!(e instanceof RPCError)) throw e;
                return;
            }
            const navButton = this.el.querySelector('header .o_wsale_my_wish');
            this.wishlistProductIds.push(productId);
            sessionStorage.setItem(
                'website_sale_wishlist_product_ids', JSON.stringify(this.wishlistProductIds)
            );
            this._updateWishlistView();
            wSaleUtils.animateClone($(navButton), $(form), 25, 40);
            // If `onChangeVariant` is called at the same time as this method, disable the button
            // again (iff `productId` hasn't changed).
            let currentProductId = this._getProductId(el);
            if (productId === currentProductId) {
                this._updateDisabled(el, true);
            }
        }
    }

    _getProductId(el) {
        let productId = el.dataset.productProductId;
        if (el.classList.contains('o_add_wishlist_dyn')) {
            productId = el.closest('.js_product').querySelector('.product_id:checked').value;
        }
        return parseInt(productId);
    }

    _updateDisabled(el, isDisabled) {
        el.disabled = isDisabled;
        el.classList.toggle('disabled', isDisabled);
    }

    _updateWishlistView() {
        const wishButton = this.el.querySelector('.o_wsale_my_wish');
        if (wishButton.classList.contains('o_wsale_my_wish_hide_empty')) {
            wishButton.classList.toggle('d-none', !this.wishlistProductIds.length);
        }
        wishButton.querySelector('.my_wish_quantity').textContent = this.wishlistProductIds.length;
    }

    _updateWishlistButton(button, productId) {
        const isDisabled = this.wishlistProductIds.includes(parseInt(productId));
        this._updateDisabled(button, isDisabled);
        button.dataset.productProductId = productId;
    }

    async _removeWish(e, deferredRedirect) {
        const tr = e.currentTarget.parents('tr'); // TODO(loti): `parents` is jQuery, not standard JS.
        const wish = tr.dataset.wishId;
        const productId = tr.dataset.productId;

        await this.waitFor(rpc('/shop/wishlist/remove/' + wish));
        tr.style.display = 'none';

        this.wishlistProductIds = this.wishlistProductIds.filter((id) => id !== productId);
        sessionStorage.setItem(
            'website_sale_wishlist_product_ids', JSON.stringify(this.wishlistProductIds)
        );
        if (!this.wishlistProductIds.length) {
            if (deferredRedirect) {
                await this.waitFor(deferredRedirect);
                this._redirectNoWish();
            }
        }
        this._updateWishlistView();
    }

    _addOrMoveWish(ev) {
        const td = ev.currentTarget.parentElement;

        const productId = parseInt(
            td.querySelector('input[type="hidden"][name="product_id"]').value
        );
        const productTemplateId = parseInt(
            td.querySelector('input[type="hidden"][name="product_template_id"]').value
        );
        const isCombo = td.querySelector(
            'input[type="hidden"][name="product_type"]'
        )?.value === 'combo';
        const showQuantity = Boolean(ev.currentTarget.dataset.showQuantity);

        const addToCart = this.services['cart'].add({
            productTemplateId: productTemplateId,
            productId: parseInt(productId, 10),
            isCombo: isCombo,
        }, {
            showQuantity: showQuantity,
        });

        if (!document.getElementById('b2b_wish').checked) {
            this._removeWish(ev, addToCart);
        }
    }

    _redirectNoWish() {
        window.location.href = '/shop/cart';
    }
}

registry
    .category('public.interactions')
    .add('website_sale_wishlist.product_wishlist', ProductWishlist);
