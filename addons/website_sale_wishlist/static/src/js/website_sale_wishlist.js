/** @odoo-module alias=website_sale_wishlist.wishlist **/

import publicWidget from "web.public.widget";
import wSaleUtils from "website_sale.utils";
import VariantMixin from "website_sale.SaleVariantMixin";

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
    willStart: function () {
        var self = this;
        var def = this._super.apply(this, arguments);
        var wishDef;
        if (this.wishlistProductIDs.length != +$('#top_menu .my_wish_quantity').text()) {
            wishDef = $.get('/shop/wishlist', {
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
        if (this.$('input.js_product_change').length) { // manage "List View of variants"
            this.$('input.js_product_change:checked').first().trigger('change');
        } else {
            this.$('input.product_id').first().trigger('change');
        }

        return def;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _addNewProducts: function ($el) {
        const self = this;

        let productID = $el.data('product-product-id');
        let productTemplateID = $el.data('product-template-id');
        let $form = undefined; // if we have the product, the form is not necessary
        if (!(productID && productTemplateID)) {
            // in case of dynamic attributes (we don't have the product id), the product
            // configuration form is needed for the selectOrCreateProduct call.
            $form = $('div#product_details > div > form');
        }

        // disable the 'Add To Wishlist' button
        $el.prop("disabled", true).addClass('disabled');

        this.selectOrCreateProduct(
            $form, // not used, we have a product
            productID,
            productTemplateID,
            false
        ).then(function (productId) {
            productId = parseInt(productId, 10);

            if (productId && !self.wishlistProductIDs.includes(productId)) {
                return self._rpc({
                    route: '/shop/wishlist/add',
                    params: {
                        product_id: productId,
                    },
                }).then(function () {
                    self.wishlistProductIDs.push(productId);
                    sessionStorage.setItem('website_sale_wishlist_product_ids', JSON.stringify(self.wishlistProductIDs));
                    self._updateWishlistView();
                    // It might happen that `onChangeVariant` is called at the same time as this function.
                    // In this case we need to set the button to disabled again.
                    // Do this only if the productID is still the same.
                    let currentProductId = $el.data('product-product-id');
                    if ($el.hasClass('o_add_wishlist_dyn')) {
                        currentProductId = parseInt($el.closest('.js_product').find('.product_id:checked').val());
                    }
                    if (productId === currentProductId) {
                        $el.prop("disabled", true).addClass('disabled');
                    }
                }).guardedCatch(function () {
                    $el.prop("disabled", false).removeClass('disabled');
                });
            }
        }).guardedCatch(function () {
            $el.prop("disabled", false).removeClass('disabled');
        });
    },
    /**
     * @private
     */
    _updateWishlistView: function () {
        const $wishButton = $('.o_wsale_my_wish');
        if ($wishButton.hasClass('o_wsale_my_wish_hide_empty')) {
            $wishButton.toggleClass('d-none', !this.wishlistProductIDs.length);
        }
        $wishButton.find('.my_wish_quantity').text(this.wishlistProductIDs.length);
    },
    /**
     * @private
     */
    _removeWish: function (e, deferred_redirect) {
        var tr = $(e.currentTarget).parents('tr');
        var wish = tr.data('wish-id');
        var product = tr.data('product-id');
        var self = this;

        this._rpc({
            route: '/shop/wishlist/remove/' + wish,
        }).then(function () {
            $(tr).hide();
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
        var tr = $(e.currentTarget).parents('tr');
        var product = tr.data('product-id');
        $('.o_wsale_my_cart').removeClass('d-none');

        if ($('#b2b_wish').is(':checked')) {
            return this._addToCart(product, tr.find('add_qty').val() || 1);
        } else {
            var adding_deffered = this._addToCart(product, tr.find('add_qty').val() || 1);
            this._removeWish(e, adding_deffered);
            return adding_deffered;
        }
    },
    /**
     * @private
     */
    _addToCart: function (productID, qty) {
        const $tr = this.$(`tr[data-product-id="${productID}"]`);
        const productTrackingInfo = $tr.data('product-tracking-info');
        if (productTrackingInfo) {
            productTrackingInfo.quantity = qty;
            $tr.trigger('add_to_cart_event', [productTrackingInfo]);
        }
        return this._rpc({
            route: "/shop/cart/update_json",
            params: this._getCartUpdateJsonParams(productID, qty),
        }).then(function (data) {
            sessionStorage.setItem('website_sale_cart_quantity', data.cart_quantity);
            wSaleUtils.updateCartNavBar(data);
            wSaleUtils.showWarning(data.warning);
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
        this._addNewProducts($(ev.currentTarget));
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onChangeVariant: function (ev) {
        const productID = parseInt($(ev.target).val(), 10);
        const $addToWishlistButton = $('.o_add_wishlist_dyn');

        if (!this.wishlistProductIDs.includes(productID)) {
            $addToWishlistButton.prop("disabled", false).removeClass('disabled').removeAttr('disabled');
        } else {
            $addToWishlistButton.prop("disabled", true).addClass('disabled').attr('disabled', 'disabled');
        }
        $addToWishlistButton.data('product-product-id', productID);
    },
    /**
     * Triggered when the customized view "product_variants" is enabled, because customers choose
     * variants directly, and not configuration of attributes anymore.
     *
     * @private
     * @param {Event} ev
     */
    _onChangeProduct: function (ev) {
        const productID = parseInt(ev.currentTarget.value, 10);
        const $addToWishlistButton = $('.o_add_wishlist_dyn');

        if (!this.wishlistProductIDs.includes(productID)) {
            $addToWishlistButton.prop("disabled", false).removeClass('disabled').removeAttr('disabled');
        } else {
            $addToWishlistButton.prop("disabled", true).addClass('disabled').attr('disabled', 'disabled');
        }

        $addToWishlistButton.data('product-product-id', productID);
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
        this.$('.wishlist-section .o_wish_add').addClass('disabled');
        this._addOrMoveWish(ev).then(function () {
            self.$('.wishlist-section .o_wish_add').removeClass('disabled');
        });
    },
});
