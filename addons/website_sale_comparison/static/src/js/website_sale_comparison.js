odoo.define('website_sale_comparison.comparison', function (require) {
"use strict";

var ajax = require('web.ajax');
var core = require('web.core');
var _t = core._t;
var utils = require('web.utils');
var Widget = require('web.Widget');
var website = require('web_editor.base');
var website_sale_utils = require('website_sale.utils');

if(!$('.oe_website_sale').length) {
    return $.Deferred().reject("DOM doesn't contain '.oe_website_sale'");
}

var qweb = core.qweb;
ajax.loadXML('/website_sale_comparison/static/src/xml/comparison.xml', qweb);

var ProductComparison = Widget.extend({
    template:"product_comparison_template",
    events: {
        'click .o_product_panel_header': 'toggle_panel',
    },
    product_data: {},
    init: function(){
        this.comparelist_product_ids = JSON.parse(utils.get_cookie('comparelist_product_ids') || '[]');
        this.product_compare_limit = 4;
    },
    start:function(){
        var self = this;
        self.load_products(this.comparelist_product_ids).then(function() {
            self.update_content(self.comparelist_product_ids, true);
            if (self.comparelist_product_ids.length) {
                $('.o_product_feature_panel').show();
                self.update_comparelist_view();
            }
        });

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
            if (self.comparelist_product_ids.length < self.product_compare_limit) {
                var prod = $(this).data('product-product-id');
                if (e.currentTarget.classList.contains('o_add_compare_dyn')) {
                    prod = parseInt($(this).parent().find('.product_id').val());
                }
                self.add_new_products(prod);
                website_sale_utils.animate_clone($('#comparelist .o_product_panel_header'), $(this).closest('form'), -50, 10);
            } else {
                self.$('.o_comparelist_limit_warning').show();
                self.show_panel(true);
            }
        });

        $('body').on('click', '.comparator-popover .o_comparelist_products .o_remove', function (e){
            self.rm_from_comparelist(e);
        });
        $("#o_comparelist_table tr").click(function(){
            $($(this).data('target')).children().slideToggle(100);
            $(this).find('.fa-chevron-circle-down, .fa-chevron-circle-right').toggleClass('fa-chevron-circle-down fa-chevron-circle-right');
        });
    },
    load_products:function(product_ids) {
        var self = this;
        return ajax.jsonRpc('/shop/get_product_data', 'call', {
            'product_ids': product_ids,
            'cookies': JSON.parse(utils.get_cookie('comparelist_product_ids') || '[]'),
        }).then(function (data) {
            self.comparelist_product_ids = JSON.parse(data.cookies);
            delete data.cookies;
            _.each(data, function(product) {
                self.product_data[product.product.id] = product;
            });
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
        $('.o_product_feature_panel').show();
        if (!_.contains(self.comparelist_product_ids, product_id)) {
            self.comparelist_product_ids.push(product_id);
            if(_.has(self.product_data, product_id)){
                self.update_content([product_id], false);
            } else {
                self.load_products([product_id]).then(function(){
                    self.update_content([product_id], false);
                });
            }
        }
        self.update_cookie();
    },
    update_content:function(product_ids, reset) {
        var self = this;
        if (reset) {
            self.$('.o_comparelist_products .o_product_row').remove();
        }
        _.each(product_ids, function(res) {
            var $template = self.product_data[res].render;
            self.$('.o_comparelist_products').append($template);
        });
        this.refresh_panel();
    },
    rm_from_comparelist: function(e){
        this.comparelist_product_ids = _.without(this.comparelist_product_ids, $(e.currentTarget).data('product_product_id'));
        $(e.currentTarget).parents('.o_product_row').remove();
        this.update_cookie();
        $('.o_comparelist_limit_warning').hide();
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
            $('.o_product_feature_panel').hide();
            this.toggle_panel();
        } else {
            this.$('.o_comparelist_products').show();
            if (this.comparelist_product_ids.length >=2) {
                this.$('.o_comparelist_button').show();
                this.$('.o_comparelist_button a').attr('href', '/shop/compare/?products='+this.comparelist_product_ids.toString());
            }
        }
    }
});

website.ready().done(function() {
    new ProductComparison().appendTo('.oe_website_sale');
});

});
