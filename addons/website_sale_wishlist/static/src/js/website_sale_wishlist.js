odoo.define('website_sale_wishlist.wishlist', function (require) {
"use strict";

var publicWidget = require('web.public.widget');
var wSaleUtils = require('website_sale.utils');
var VariantMixin = require('sale.VariantMixin');

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
        this.wishlistProductIDs = [];
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

        var wishDef = $.get('/shop/wishlist', {
            count: 1,
        }).then(function (res) {
            self.wishlistProductIDs = JSON.parse(res);
        });

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
        var self = this;
        var productID = $el.data('product-product-id');
        if ($el.hasClass('o_add_wishlist_dyn')) {
            productID = parseInt($el.closest('.js_product').find('.product_id:checked').val());;
        }
        var $form = $el.closest('form');
        var templateId = $form.find('.product_template_id').val();
        // when adding from /shop instead of the product page, need another selector
        if (!templateId) {
            templateId = $el.data('product-template-id');
        }
        $el.prop("disabled", true).addClass('disabled');
        var productReady = this.selectOrCreateProduct(
            $el.closest('form'),
            productID,
            templateId,
            false
        );

        productReady.then(function (productId) {
            productId = parseInt(productId, 10);

            if (productId && !_.contains(self.wishlistProductIDs, productId)) {
                return self._rpc({
                    route: '/shop/wishlist/add',
                    params: {
                        product_id: productId,
                    },
                }).then(function () {
                    var $navButton = $('header .o_wsale_my_wish').first();
                    self.wishlistProductIDs.push(productId);
                    self._updateWishlistView();
                    wSaleUtils.animateClone($navButton, $el.closest('form'), 25, 40);
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

        this.wishlistProductIDs = _.without(this.wishlistProductIDs, product);
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
        var $navButton = $('header .o_wsale_my_cart').first();
        var tr = $(e.currentTarget).parents('tr');
        var product = tr.data('product-id');
        $('.o_wsale_my_cart').removeClass('d-none');
        wSaleUtils.animateClone($navButton, tr, 25, 40);

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
            params: {
                product_id: parseInt(productID, 10),
                add_qty: parseInt(qty, 10),
                display: false,
            },
        }).then(function (data) {
            wSaleUtils.updateCartNavBar(data);
            wSaleUtils.showWarning(data.warning);
        });
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
        var $input = $(ev.target);
        var $parent = $input.closest('.js_product');
        var $el = $parent.find("[data-action='o_wishlist']");
        if (!_.contains(this.wishlistProductIDs, parseInt($input.val(), 10))) {
            $el.prop("disabled", false).removeClass('disabled').removeAttr('disabled');
        } else {
            $el.prop("disabled", true).addClass('disabled').attr('disabled', 'disabled');
        }
        $el.data('product-product-id', parseInt($input.val(), 10));
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onChangeProduct: function (ev) {
        var productID = ev.currentTarget.value;
        var $el = $(ev.target).closest('.js_add_cart_variants').find("[data-action='o_wishlist']");

        if (!_.contains(this.wishlistProductIDs, parseInt(productID, 10))) {
            $el.prop("disabled", false).removeClass('disabled').removeAttr('disabled');
        } else {
            $el.prop("disabled", true).addClass('disabled').attr('disabled', 'disabled');
        }
        $el.data('product-product-id', productID);
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
        var self = this;
        this.$('.wishlist-section .o_wish_add').addClass('disabled');
        this._addOrMoveWish(ev).then(function () {
            self.$('.wishlist-section .o_wish_add').removeClass('disabled');
        });
    },
});
});
