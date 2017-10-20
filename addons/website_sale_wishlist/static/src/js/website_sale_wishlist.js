odoo.define('website_sale_wishlist.wishlist', function (require) {
"use strict";

require('web.dom_ready');
var ajax = require('web.ajax');
var rpc = require('web.rpc');
var Widget = require('web.Widget');
var base = require('web_editor.base');
var website_sale_utils = require('website_sale.utils');
var weContext = require('web_editor.context');

if(!$('.oe_website_sale').length) {
    return $.Deferred().reject("DOM doesn't contain '.oe_website_sale'");
}

var ProductWishlist = Widget.extend({
    events: {
        'click #my_wish': 'display_wishlist',
    },
    init: function(){
        var self = this;
        this.wishlist_product_ids = [];
        $.get('/shop/wishlist', {'count': 1}).then(function(res) {
            self.wishlist_product_ids = JSON.parse(res);
            self.update_wishlist_view();
        });
        $('.oe_website_sale .o_add_wishlist, .oe_website_sale .o_add_wishlist_dyn').click(function (e){
            self.add_new_products($(this), e);
        });

        if ($('.wishlist-section').length) {
            $('.wishlist-section a.o_wish_rm').on('click', function (e){ self.wishlist_rm(e, false); });
            $('.wishlist-section a.o_wish_add').on('click', function (e){ self.wishlist_add_or_mv(e); });
        }

        $('.oe_website_sale').on('change', 'input.js_variant_change, select.js_variant_change, ul[data-attribute_value_ids]', function(ev) {
            var $ul = $(ev.target).closest('.js_add_cart_variants');
            var $parent = $ul.closest('.js_product');
            var $product_id = $parent.find('.product_id').first();
            var $el = $parent.find("[data-action='o_wishlist']");
            if (!_.contains(self.wishlist_product_ids, parseInt($product_id.val(), 10))) {
                $el.prop("disabled", false).removeClass('disabled').removeAttr('disabled');
            }
            else {
                $el.prop("disabled", true).addClass('disabled').attr('disabled', 'disabled');
            }
        });
    },
    add_new_products:function($el, e){
        var self = this;
        var product_id = $el.data('product-product-id');
        if (e.currentTarget.classList.contains('o_add_wishlist_dyn')) {
            product_id = parseInt($el.parent().find('.product_id').val());
        }
        if (!_.contains(self.wishlist_product_ids, product_id)) {
            return ajax.jsonRpc('/shop/wishlist/add', 'call', {
                'product_id': product_id
            }).then(function () {
                self.wishlist_product_ids.push(product_id);
                self.update_wishlist_view();
                website_sale_utils.animate_clone($('#my_wish'), $el.closest('form'), 25, 40);
                $el.prop("disabled", true).addClass('disabled');
            });
        }
    },
    display_wishlist: function() {
        if (this.wishlist_product_ids.length === 0) {
            this.update_wishlist_view();
            this.redirect_no_wish();
        }
        else {
            window.location = '/shop/wishlist';
        }
    },
    update_wishlist_view: function() {
        if (this.wishlist_product_ids.length > 0) {
            $('#my_wish').show();
            $('.my_wish_quantity').text(this.wishlist_product_ids.length);
        }
        else {
            $('#my_wish').hide();
        }
    },
    wishlist_rm: function(e, deferred_redirect){
        var tr = $(e.currentTarget).parents('tr');
        var wish = tr.data('wish-id');
        var product = tr.data('product-id');
        var self = this;

        rpc.query({
                model: 'product.wishlist',
                method: 'write',
                args: [[wish], { active: false }, weContext.getExtra()],
            })
            .then(function(){
                $(tr).hide();
            });

        this.wishlist_product_ids = _.without(this.wishlist_product_ids, product);
        if (this.wishlist_product_ids.length === 0) {
            deferred_redirect = deferred_redirect ? deferred_redirect : $.Deferred();
            deferred_redirect.then(function() {
                self.redirect_no_wish();
            });
        }
        this.update_wishlist_view();
    },
    wishlist_add_or_mv: function(e){
        return $('#b2b_wish').is(':checked') ? this.wishlist_add(e) : this.wishlist_mv(e);
    },
    wishlist_add: function(e){
        var tr = $(e.currentTarget).parents('tr');
        var product = tr.data('product-id');

        // can be hidden if empty
        $('#my_cart').removeClass('hidden');
        website_sale_utils.animate_clone($('#my_cart'), tr, 25, 40);
        this.add_to_cart(product, tr.find('qty').val() || 1);
    },
    wishlist_mv: function(e){
        var tr = $(e.currentTarget).parents('tr');
        var product = tr.data('product-id');

        $('#my_cart').removeClass('hidden');
        website_sale_utils.animate_clone($('#my_cart'), tr, 25, 40);
        var adding_deffered = this.add_to_cart(product, tr.find('qty').val() || 1);
        this.wishlist_rm(e, adding_deffered);
    },
    add_to_cart: function(product_id, qty_id) {
        var add_to_cart = ajax.jsonRpc("/shop/cart/update_json", 'call', {
            'product_id': parseInt(product_id, 10),
            'add_qty': parseInt(qty_id, 10),
            'display': false,
        });

        add_to_cart.then(function(resp) {
            if (resp.warning) {
                if (! $('#data_warning').length) {
                    $('.wishlist-section').prepend('<div class="mt16 alert alert-danger alert-dismissable" role="alert" id="data_warning"></div>');
                }
                var cart_alert = $('.wishlist-section').parent().find('#data_warning');
                cart_alert.html('<button type="button" class="close" data-dismiss="alert" aria-hidden="true">&times;</button> ' + resp.warning);
            }
            $('.my_cart_quantity').html(resp.cart_quantity || '<i class="fa fa-warning" /> ');
        });
        return add_to_cart;
    },
    redirect_no_wish: function() {
        window.location = '/shop/cart';
    }
});

new ProductWishlist();

});
