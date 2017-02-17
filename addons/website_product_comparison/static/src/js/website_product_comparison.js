odoo.define('website_product_comparison.comparison', function (require) {
"use strict";

var ajax = require('web.ajax');
var core = require('web.core');
var _t = core._t;
var utils = require('web.utils');
var Widget = require('web.Widget');
var website = require('web_editor.base');

if(!$('.oe_website_sale').length) {
    return $.Deferred().reject("DOM doesn't contain '.oe_website_sale'");
}

var qweb = core.qweb;
ajax.loadXML('/website_product_comparison/static/src/xml/comparison.xml', qweb);

var ProductFeaturePanel = Widget.extend({
    template: 'product_feature_template',
    events: {},
    product_data: {},
    init: function() {},
    show: function() {
        $('.o_product_feature_panel').show();
    },
    load_products:function(product_ids) {
        var self = this;
        return ajax.jsonRpc('/shop/get_product_data', 'call', {
            'product_ids': product_ids
        }).then(function (data) {
            _.each(data, function(product) {
                self.product_data[product.product.id] = product;
            });
        });
    },
    animate_clone: function(cart, $elem, offset_top, offset_left) {
        cart.find('.o_product_circle').addClass('o_red_highlight o_shadow_animation').delay(500).queue(function(){
            $(this).removeClass("o_shadow_animation").dequeue();
        });
        var imgtodrag = $elem.find('img').eq(0);
        if (imgtodrag.length) {
            var imgclone = imgtodrag.clone()
            .offset({
                top: imgtodrag.offset().top,
                left: imgtodrag.offset().left
            })
            .addClass('o_product_comparison_animate')
            .appendTo($('body'))
            .animate({
                'top': cart.offset().top + offset_top,
                'left': cart.offset().left + offset_left,
                'width': 75,
                'height': 75
            }, 1000, 'easeInOutExpo');

            imgclone.animate({
                'width': 0,
                'height': 0
            }, function () {
                $(this).detach();
            });
        }
    }
});

var ProductComparison = Widget.extend({
    template:"product_comparison_template",
    events: {
        'click .o_product_panel_header': 'toggle_panel',
    },
    init: function(parent){
        this.parent = parent;
        this.comparelist_product_ids = JSON.parse(utils.get_cookie('comparelist_product_ids') || 'null') || [];
        this.product_compare_limit = 4;
        this.parent.show();
    },
    start:function(){
        var self = this;
        self.popover = $('#comparelist .o_product_panel_header').popover({
            trigger: 'manual',
            animation: true,
            html: true,
            title: function () {
                return _t("Compare Products");
            },
            container: '.o_product_feature_panel',
            placement: 'top',
            template: '<div style="width:600px;" class="popover comparator-popover" role="tooltip"><div class="arrow"></div><h3 class="popover-title"></h3><div class="popover-content"></div></div>',
            content: function() {
                return $('#comparelist .o_product_panel_content').html();
            }
        });
        $('.oe_website_sale .o_add_compare, .oe_website_sale .o_add_compare_dyn').click(function (e){
            self.parent.animate_clone($('#comparelist .o_product_panel_header'), $(this).closest('form'), -50, 10);
            if (self.comparelist_product_ids.length < self.product_compare_limit) {
                var prod = $(this).data('product-product-id');
                if (e.currentTarget.classList.contains('o_add_compare_dyn')) {
                    prod = parseInt($(this).parent().find('.product_id').val());
                }
                self.add_new_products(prod);
            } else {
                self.$('.o_comparelist_limit_warning').show();
                self.show_panel(false);
            }
        });
        self.parent.load_products(this.comparelist_product_ids).then(function() {
            self.update_content(self.comparelist_product_ids, true);
        });

        $('body').on('click', '.comparator-popover .o_comparelist_products .o_remove', function (e){
            self.rm_from_comparelist(e);
        });
        $("#o_comparelist_table tr").click(function(){
            $($(this).data('target')).children().slideToggle(100);
            $(this).find('.fa-chevron-circle-down, .fa-chevron-circle-right').toggleClass('fa-chevron-circle-down fa-chevron-circle-right');
        });
    },
    toggle_panel: function() {
        $('#comparelist .o_product_panel_header').popover('toggle');
    },
    show_panel: function(force) {
        if ((!$('.comparator-popover').length) || force) {
            $('#comparelist .o_product_panel_header').popover('show');
        }
    },
    refresh_panel: function() {
        if ($('.comparator-popover').length) {
            $('#comparelist .o_product_panel_header').popover('show');
        }
    },
    add_new_products:function(product_id){
        var self = this;
        self.$('.o_comparelist_warning').hide();
        if (!_.contains(self.comparelist_product_ids, product_id)) {
            self.comparelist_product_ids.push(product_id);
            if(_.has(self.parent.product_data, product_id)){
                self.update_content([product_id], false);
            } else {
                self.parent.load_products([product_id]).then(function(){
                    self.update_content([product_id], false);
                });
            }
        }
    },
    update_content:function(product_ids, reset) {
        var self = this;
        if (reset) {
            self.$('.o_comparelist_products .o_product_row').remove();
        }
        if (product_ids.length) {
            var category = self.check_product_category(self.parent.product_data[product_ids[0]]);
            if (category) {
                _.each(product_ids, function(res) {
                    self.$('.o_product_panel_empty').hide();
                    var $template = self.parent.product_data[res].render;
                    self.$('.o_comparelist_products').append($template);
                });
                self.update_cookie();
            }
        }
        this.refresh_panel();
    },
    check_product_category: function(data) {
        var category_ids = $('#comparelist .o_product_row:first').data('category_ids');
        if (category_ids){
            var categories = JSON.parse("[" + category_ids + "]"); // TO DO : use parent
            if (!_.intersection(categories, data.product.public_categ_ids).length) {
                this.$('.o_comparelist_warning').show();
                this.$('#comparelist_alert').text(data.product.name);
                this.show_panel(true);
                this.comparelist_product_ids = _.without(this.comparelist_product_ids, data.product.id);
                return false;
            }
        }
        $('.o_comparelist_warning').hide();
        return true;
    },
    rm_from_comparelist: function(e){
        this.comparelist_product_ids = _.without(this.comparelist_product_ids, $(e.currentTarget).data('product_product_id'));
        $(e.currentTarget).parents('.o_product_row').remove();
        this.$('.o_comparelist_warning, .o_comparelist_limit_warning').hide();
        this.update_cookie();
        // force refresh to reposition popover
        this.update_content(this.comparelist_product_ids, true);
    },
    update_cookie: function(){
        document.cookie = 'comparelist_product_ids=' + JSON.stringify(this.comparelist_product_ids) + '; path=/';
        this.update_comparelist_view();
    },
    update_comparelist_view: function() {
        this.$('.o_product_circle').text(this.comparelist_product_ids.length);
        this.$('.o_comparelist_button').hide();
        if (_.isEmpty(this.comparelist_product_ids)) {
            this.$('.o_product_panel_empty').show();
            this.$('.o_comparelist_products').hide();
        } else {
            this.$('.o_comparelist_products').show();
            if (this.comparelist_product_ids.length >=2) {
                this.$('.o_comparelist_button').show();
                this.$('.o_comparelist_button a').attr('href', '/shop/compare/?products='+this.comparelist_product_ids.toString());
            }
        }
    }
});

var ProductWishlist = Widget.extend({
    template:"product_wishlist_template",
    events: {
        'click .o_product_panel_header': 'display_wishlist',
    },
    init: function(parent){
        var self = this;
        this.parent = parent;
        this.wishlist_product_ids = [];
        if (!odoo.session_info.is_publicuser) {
            $.get('/shop/wishlist', {'count': 1}).then(function(res) {
                self.wishlist_product_ids = JSON.parse(res);
                self.update_wishlist_view();
            });
        }
        this.parent.show();
    },
    start:function(){
        var self = this;
        $('.oe_website_sale .o_add_wishlist').click(function (){
            if (!odoo.session_info.is_publicuser) {
                self.parent.animate_clone($('#wishlist .o_product_panel_header'), $(this).closest('form'), -50, 10);
            }
            self.add_new_products($(this));
        });
        if ($('.wishlist-section').length) {
            $('.wishlist-section a.o_wish_rm').on('click', function (e){ self.wishlist_rm(e); });
            $('.wishlist-section a.o_wish_add').on('click', function (e){ self.wishlist_add(e); });
            $('.wishlist-section a.o_wish_mv').on('click', function (e){ self.wishlist_mv(e); });
        }
    },
    add_new_products:function($el){
        var self = this;
        var product_id = $el.data('product-product-id');
        if (odoo.session_info.is_publicuser){
            this.warning_not_logged();
        } else {
            if (!_.contains(self.wishlist_product_ids, product_id)) {
                return ajax.jsonRpc('/shop/wishlist/add', 'call', {
                    'product_id': product_id
                }).then(function () {
                    self.wishlist_product_ids.push(product_id);
                    self.update_wishlist_view();
                });
            }
        }
    },
    display_wishlist: function() {
        if (odoo.session_info.is_publicuser) {
            this.warning_not_logged();
        }
        else if (this.wishlist_product_ids.length === 0) {
            this.update_wishlist_view();
            this.redirect_no_wish();
        }
        else {
            window.location = '/shop/wishlist';
        }
    },
    update_wishlist_view: function() {
        this.$('.o_product_circle').text(this.wishlist_product_ids.length);
    },
    wishlist_rm: function(e){
        var tr = $(e.currentTarget).parents('tr');
        var wish = tr.data('wish-id');
        var product = tr.data('product-id');
        ajax.jsonRpc('/shop/wishlist/rm', 'call', {'wish': wish}).then(function() {
            $(tr).hide();
        });
        this.wishlist_product_ids = _.without(this.wishlist_product_ids, product);
        if (this.wishlist_product_ids.length === 0) {
            this.redirect_no_wish();
        }
        this.update_wishlist_view();
    },
    wishlist_add: function(e){
        var tr = $(e.currentTarget).parents('tr');
        var product = tr.data('product-id');

        // can be hidden if empty
        $('.my_cart_quantity').parents('li').removeClass('hidden');
        this.parent.animate_clone($('.my_cart_quantity').parents('li'), tr, 0, 0);
        this.add_to_cart(product, tr.find('qty').val() || 1);
    },
    wishlist_mv: function(e){
        var tr = $(e.currentTarget).parents('tr');
        var product = tr.data('product-id');

        $('.my_cart_quantity').parents('li').removeClass('hidden');
        this.parent.animate_clone($('.my_cart_quantity').parents('li'), tr, 0, 0);
        this.add_to_cart(product, tr.find('qty').val() || 1);
        this.wishlist_rm(e);
    },
    add_to_cart: function(product_id, qty_id) {
        ajax.jsonRpc("/shop/cart/update_json", 'call', {
            'product_id': parseInt(product_id, 10),
            'add_qty': parseInt(qty_id, 10)
        }).then(function (data) {
            var $q = $(".my_cart_quantity");
            if (data.cart_quantity) {
                $q.html(data.cart_quantity).hide().fadeIn(600);
            }
        });
    },
    redirect_no_wish: function() {
        window.location = '/shop';
    },
    warning_not_logged: function() {
        window.location = '/shop/wishlist';
    }
});

website.ready().done(function() {
    $(".o_specification_panel").click(function(){
        $(this).parent().find('.panel-body').slideToggle('normal');
        $(this).find('.fa-angle-double-right,.fa-angle-double-down').toggleClass('fa-angle-double-right fa-angle-double-down');
    });

    var comparatorProm = ajax.jsonRpc('/shop/compare_active', 'call', {});
    var wishlistProm = ajax.jsonRpc('/shop/wishlist_active', 'call', {});

    $.when(comparatorProm, wishlistProm).done(function (comparator, wishlist) {
        if (comparator || wishlist) {
            var parent = new ProductFeaturePanel();
            parent.appendTo('.oe_website_sale');

            if (comparator) {
                new ProductComparison(parent).appendTo('.o_product_feature_panel');
            }
            if (wishlist) {
                new ProductWishlist(parent).appendTo('.o_product_feature_panel');
            }
        }
    });
});

});
