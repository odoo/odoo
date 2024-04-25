/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import wSaleUtils from "@website_sale/js/website_sale_utils";
import VariantMixin from "@website_sale/js/sale_variant_mixin";
import { rpc, RPCError } from "@web/core/network/rpc";

// VariantMixin events are overridden on purpose here
// to avoid registering them more than once since they are already registered
// in website_sale.js
publicWidget.registry.ProductWishlist = publicWidget.Widget.extend(VariantMixin, {
    selector: '.oe_website_sale',
    events: {
        'click .o_wsale_my_wish': '_onClickMyWish',
        'click .o_add_wishlist, .o_add_wishlist_dyn': '_onClickAddWish',
        'change input.product_id': '_onChangeVariant',
        'change input.js_product_change': '_onChangeProduct',
        'click .wishlist-section .o_wish_rm': '_onClickWishRemove',
        'click .wishlist-section .o_wish_add': '_onClickWishAdd',
    },

    /**
     * @constructor
     */
    init: function (parent) {
        this._super.apply(this, arguments);
        this.wishlistProductIDs = JSON.parse(sessionStorage.getItem('website_sale_wishlist_product_ids') || '[]');
    },
    /**
     * Gets the current wishlist items.
     * In editable mode, do nothing instead.
     *
     * @override
     */
    willStart: async function () {
        const self = this;
        const def = this._super.apply(this, arguments);
        let wishDef;
        if (this.wishlistProductIDs.length != + this.el.querySelector('header#top .my_wish_quantity').textContent) {
            wishDef = await fetch('/shop/wishlist', {
                count: 1,
            }).then(function (res) {
                self.wishlistProductIDs = JSON.parse(res);
                sessionStorage.setItem('website_sale_wishlist_product_ids', res);
            });

        }
        return Promise.all([def, wishDef]);
    },
    /**
     * Updates the wishlist view (navbar) & the wishlist button (product page).
     * In editable mode, do nothing instead.
     *
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);

        this._updateWishlistView();
        // trigger change on only one input
        if (this.el.querySelector('input.js_product_change').length) { // manage "List View of variants"
            let checkedProductInput = this.el.querySelector('input.js_product_change:checked');
            // TODO-visp: Check this also
            // checkedProductInput.dispatchEvent(new Event('change'));
            $(checkedProductInput).trigger('change');

        } else {
            let inputProductId = this.el.querySelector('input.product_id');
            // TODO-visp: Check this also
            // inputProductId.dispatchEvent(new Event('change'));
            $(inputProductId).trigger('change');
        }

        return def;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _addNewProducts: function (el) {
        const self = this;
        let productID = el.dataset.productProductId;
        if (el.classList.contains('o_add_wishlist_dyn')) {
            productID = parseInt(el.closest('.js_product').querySelector('.product_id:checked').value);;
        }
        const form = el.closest('form');
        let templateId = form.querySelector('.product_template_id').value;
        // when adding from /shop instead of the product page, need another selector
        if (!templateId) {
            templateId = el.dataset.productTemplateId;
        }
        el.disabled = true;
        el.classList.add('disabled');
        const productReady = this.selectOrCreateProduct(
            el.closest('form'),
            productID,
            templateId,
        );

        productReady.then(function (productId) {
            productId = parseInt(productId, 10);

            if (productId && !self.wishlistProductIDs.includes(productId)) {
                return rpc('/shop/wishlist/add', {
                    product_id: productId,
                }).then(function () {
                    const navButton = this.el.querySelector('header .o_wsale_my_wish');
                    self.wishlistProductIDs.push(productId);
                    sessionStorage.setItem('website_sale_wishlist_product_ids', JSON.stringify(self.wishlistProductIDs));
                    self._updateWishlistView();
                    wSaleUtils.animateClone(navButton, el.closest('form'), 25, 40);
                    // It might happen that `onChangeVariant` is called at the same time as this function.
                    // In this case we need to set the button to disabled again.
                    // Do this only if the productID is still the same.
                    let currentProductId = el.dataset.productProductId;
                    if (el.classList.contains('o_add_wishlist_dyn')) {
                        currentProductId = parseInt(el.closest('.js_product').querySelector('.product_id:checked').value);
                    }
                    if (productId === currentProductId) {
                        el.disabled = true;
                        el.classList.add('disabled');
                    }
                }).catch(function (e) {
                    el.disabled = false;
                    el.classList.remove('disabled');
                    if (!(e instanceof RPCError)) {
                        return Promise.reject(e);
                    }
                });
            }
        }).catch(function (e) {
            el.disabled = false;
            el.classList.remove('disabled');
            if (!(e instanceof RPCError)) {
                return Promise.reject(e);
            }
        });
    },
    /**
     * @private
     */
    _updateWishlistView: function () {
        const wishButton = this.el.querySelector('.o_wsale_my_wish');
        if (wishButton.classList.contains('o_wsale_my_wish_hide_empty')) {
            wishButton.classList.toggle('d-none', !this.wishlistProductIDs.length);
        }
        wishButton.querySelector('.my_wish_quantity').textContent = this.wishlistProductIDs.length;
    },
    /**
     * @private
     */
    _removeWish: function (e, deferred_redirect) {
        const tr = e.currentTarget.parents('tr');
        const wish = tr.dataset.wishId;
        const product = tr.dataset.productId;
        const self = this;

        rpc('/shop/wishlist/remove/' + wish).then(function () {
            tr.style.display = 'none';
        });

        this.wishlistProductIDs = this.wishlistProductIDs.filter((p) => p !== product);
        sessionStorage.setItem('website_sale_wishlist_product_ids', JSON.stringify(this.wishlistProductIDs));
        if (this.wishlistProductIDs.length === 0) {
            if (deferred_redirect) {
                deferred_redirect.then(function () {
                    self._redirectNoWish();
                });
            }
        }
        this._updateWishlistView();
    },
    /**
     * @private
     */
    _addOrMoveWish: function (e) {
        const tr = e.currentTarget.parents('tr');
        const product = tr.dataset.productId;
        this.el.querySelector('.o_wsale_my_cart').classList.remove('d-none');

        if (this.el.querySelector('#b2b_wish:checked')) {
            return this._addToCart(product, tr.querySelector('.add_qty').value || 1);
        } else {
            var adding_deffered = this._addToCart(product, tr.querySelector('.add_qty').value || 1);
            this._removeWish(e, adding_deffered);
            return adding_deffered;
        }
    },
    /**
     * @private
     */
    _addToCart: function (productID, qty) {
        const tr = this.el.querySelector(`tr[data-product-id="${productID}"]`);
        const productTrackingInfo = tr.dataset.productTrackingInfo;
        if (productTrackingInfo) {
            productTrackingInfo.quantity = qty;
            tr.dispatchEvent(new CustomEvent('add_to_cart_event', { detail: [productTrackingInfo] }));
        }
        const callService = this.call.bind(this)
        return rpc("/shop/cart/update_json", {
            ...this._getCartUpdateJsonParams(productID, qty),
            display: false,
        }).then(function (data) {
            wSaleUtils.updateCartNavBar(data);
            wSaleUtils.showCartNotification(callService, data.notification_info);
        });
    },
    /**
     * Get the cart update params.
     *
     * @param {string} productId
     * @param {string} qty
     */
    _getCartUpdateJsonParams(productId, qty) {
        return {
            product_id: parseInt(productId, 10),
            add_qty: parseInt(qty, 10),
            display: false,
        };
    },
    /**
     * @private
     */
    _redirectNoWish: function () {
        window.location.href = '/shop/cart';
    },


    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClickMyWish: function () {
        if (this.wishlistProductIDs.length === 0) {
            this._updateWishlistView();
            this._redirectNoWish();
            return;
        }
        window.location = '/shop/wishlist';
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onClickAddWish: function (ev) {
        this._addNewProducts(ev.currentTarget);
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onChangeVariant: function (ev) {
        const input = ev.target;
        const parent = input.closest('.js_product');
        const el = parent.querySelector("[data-action='o_wishlist']");
        if (!this.wishlistProductIDs.includes(parseInt(input.value, 10))) {
            el.disabled = false;
            el.classList.remove('disabled');
            el.removeAttribute('disabled');
        } else {
            el.disabled = true;
            el.classList.add('disabled');
            el.setAttributw('disabled', 'disabled');
        }
        el.dataset.productProductId = parseInt(input.value, 10);
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onChangeProduct: function (ev) {
        const productID = ev.currentTarget.value;
        const el = ev.target.closest('.js_add_cart_variants').querySelector("[data-action='o_wishlist']");

        if (!this.wishlistProductIDs.includes(parseInt(productID, 10))) {
            el.disabled = false;
            el.classList.remove('disabled');
            el.removeAttribute('disabled');
        } else {
            el.disabled = true;
            el.classList.add('disabled');
            el.setAttributw('disabled', 'disabled');
        }
        el.dataset.productProductId = productID;
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onClickWishRemove: function (ev) {
        this._removeWish(ev, false);
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onClickWishAdd: function (ev) {
        if (ev.currentTarget.classList.contains('disabled')) {
            ev.preventDefault();
            return;
        }
        var self = this;
        this.el.querySelector('.wishlist-section .o_wish_add').classList.add('disabled');
        this._addOrMoveWish(ev).then(function () {
            self.el.querySelector('.wishlist-section .o_wish_add').classList.remove('disabled');
        });
    },
});
