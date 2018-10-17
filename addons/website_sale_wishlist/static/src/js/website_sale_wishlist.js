odoo.define('website_sale_wishlist.wishlist', function (require) {
"use strict";

var sAnimations = require('website.content.snippets.animation');
var wSaleUtils = require('website_sale.utils');
var ProductConfiguratorMixin = require('sale.ProductConfiguratorMixin');

// ProductConfiguratorMixin events are overridden on purpose here
// to avoid registering them more than once since they are already registered
// in website_sale.js
sAnimations.registry.ProductWishlist = sAnimations.Class.extend(ProductConfiguratorMixin, {
    selector: '.oe_website_sale',
    read_events: {
        'click #my_wish': '_onClickMyWish',
        'click .o_add_wishlist, .o_add_wishlist_dyn': '_onClickAddWish',
        'change input.product_id': '_onChangeVariant',
        'change input.js_product_change': '_onChangeProduct',
        'click .wishlist-section .o_wish_rm': '_onClickWishRemove',
        'click .wishlist-section .o_wish_add': '_onClickWishAdd',
    },
    events: sAnimations.Class.events,

    start: function () {
        var self = this;
        var def = this._super.apply(this, arguments);
        if (this.editableMode) {
            return def;
        }

        this.wishlistProductIDs = [];

        var wishDef = $.get('/shop/wishlist', {
            count: 1,
        }).then(function (res) {
            self.wishlistProductIDs = JSON.parse(res);
            self._updateWishlistView();
            if ($('input.js_product_change').length) { // manage "List View of variants"
                $('input.js_product_change:checked').first().trigger('change');
            } else {
                $('input.js_variant_change').trigger('change');
            }
        });

        return $.when(def, wishDef);
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
            productID = $el.parent().find('.product_id').val();
            if (!productID) { // case List View Variants
                productID = $el.parent().find('input:checked').first().val();
            }
            productID = parseInt(productID, 10);
        }

        $el.prop("disabled", true).addClass('disabled');
        var productReady = this.selectOrCreateProduct(
            $el.closest('form'),
            productID,
            $el.closest('form').find('.product_template_id').val(),
            false
        );

        productReady.done(function (productId) {
            productId = parseInt(productId, 10);

            if (productId && !_.contains(self.wishlistProductIDs, productId)) {
                return self._rpc({
                    route: '/shop/wishlist/add',
                    params: {
                        product_id: productId,
                    },
                }).then(function () {
                    self.wishlistProductIDs.push(productId);
                    self._updateWishlistView();
                    wSaleUtils.animateClone($('#my_wish'), $el.closest('form'), 25, 40);
                }).fail(function () {
                    $el.prop("disabled", false).removeClass('disabled');
                });
            }
        }).fail(function () {
            $el.prop("disabled", false).removeClass('disabled');
        });
    },
    /**
     * @private
     */
    _updateWishlistView: function () {
        if (this.wishlistProductIDs.length > 0) {
            $('#my_wish').show();
            $('.my_wish_quantity').text(this.wishlistProductIDs.length);
        } else {
            $('#my_wish').hide();
        }
    },
    /**
     * @private
     */
    _removeWish: function (e, deferred_redirect){
        var tr = $(e.currentTarget).parents('tr');
        var wish = tr.data('wish-id');
        var product = tr.data('product-id');
        var self = this;

        this._rpc({
            route: '/shop/wishlist/remove/' + wish,
        }).done(function () {
            $(tr).hide();
        });

        this.wishlistProductIDs = _.without(this.wishlistProductIDs, product);
        if (this.wishlistProductIDs.length === 0) {
            deferred_redirect = deferred_redirect ? deferred_redirect : $.Deferred();
            deferred_redirect.then(function () {
                self._redirectNoWish();
            });
        }
        this._updateWishlistView();
    },
    /**
     * @private
     */
    _addOrMoveWish: function (e) {
        var tr = $(e.currentTarget).parents('tr');
        var product = tr.data('product-id');
        $('#my_cart').removeClass('d-none');
        wSaleUtils.animateClone($('#my_cart'), tr, 25, 40);

        if ($('#b2b_wish').is(':checked')) {
            return this._addToCart(product, tr.find('qty').val() || 1);
        } else {
            var adding_deffered = this._addToCart(product, tr.find('qty').val() || 1);
            this._removeWish(e, adding_deffered);
            return adding_deffered;
        }
    },
    /**
     * @private
     */
    _addToCart: function (productID, qty_id) {
        return this._rpc({
            route: "/shop/cart/update_json",
            params: {
                product_id: parseInt(productID, 10),
                add_qty: parseInt(qty_id, 10),
                display: false,
            },
        }).then(function (resp) {
            if (resp.warning) {
                if (! $('#data_warning').length) {
                    $('.wishlist-section').prepend('<div class="mt16 alert alert-danger alert-dismissable" role="alert" id="data_warning"></div>');
                }
                var cart_alert = $('.wishlist-section').parent().find('#data_warning');
                cart_alert.html('<button type="button" class="close" data-dismiss="alert" aria-hidden="true">&times;</button> ' + resp.warning);
            }
            $('.my_cart_quantity').html(resp.cart_quantity || '<i class="fa fa-warning" /> ');
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
