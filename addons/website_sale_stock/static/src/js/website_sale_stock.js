odoo.define('website_sale_stock.website_sale', function(require) {
'use strict';

require('web.dom_ready');
var base = require('web_editor.base');
var ajax = require('web.ajax');
var core = require('web.core');

var QWeb = core.qweb;
var xml_load = ajax.loadXML('/website_sale_stock/static/src/xml/website_sale_stock_product_availability.xml', QWeb);

if(!$('.oe_website_sale').length) {
    return $.Deferred().reject("DOM doesn't contain '.oe_website_sale'");
}

$('.oe_website_sale').each(function() {
    var oe_website_sale = this;

    // For options products
    $(oe_website_sale).on('change', 'input[name="add_qty"]', function() {
        $(oe_website_sale).find('ul[data-attribute_value_ids]').trigger('change');
    });

    $(oe_website_sale).find('input[name="add_qty"]').trigger('change');

    // Handle case when manually write in input
    $(oe_website_sale).on('change', '.js_quantity', function(event) {
        var $input = $(event.currentTarget);
        var max_qty = parseInt($input.data('max'));
        if($input.val() > max_qty) {
            $input.val(max_qty);
        }
    });


    /* Renders a specific message concerning the stock of the product
        and its variants on the product website page.
    */
    $(oe_website_sale).on('change', 'ul[data-attribute_value_ids]', function(event) {
        var $ul = $(event.target).closest('.js_add_cart_variants');
        var $parent = $ul.closest('.js_product');
        var variant_ids = JSON.parse($ul.data("attribute_value_ids").replace(/'/g, '"'));
        var values = [];
        $parent.find('input.js_variant_change:checked, select.js_variant_change').each(function() {
            values.push(+$(this).val());
        });
        var qty = $parent.find('input[name="add_qty"]').val();
        for (var k in variant_ids) {
            if (_.isEmpty(_.difference(variant_ids[k][1], values))) {
                var info = variant_ids[k][4];
                if(_.contains(['always', 'threshold'], info['inventory_availability'])) {
                    info['virtual_available'] -= parseInt(info['cart_qty']);
                    if (info['virtual_available'] < 0) {
                        info['virtual_available'] = 0;
                    }
                    // Handle case when manually write in input
                    if(qty > info['virtual_available']) {
                        $parent.find('input[name="add_qty"]').val(info['virtual_available'] || 1);
                    }
                    if(qty > info['virtual_available'] || info['virtual_available'] < 1 || qty < 1) {
                        $parent.find('#add_to_cart').addClass('disabled');
                    }
                    // For options products: if qty not available disable add to cart on change variant
                    $parent.find('.js_add').toggleClass('disabled btn', info['virtual_available'] < 1);
                }
                xml_load.then(function() {
                    $(oe_website_sale).find('.availability_message_' + info['product_template']).remove();
                    var $message = $(QWeb.render('website_sale_stock.product_availability', info));
                    $('div.availability_messages').html($message);
                });
            }
        }
    });
});

});
