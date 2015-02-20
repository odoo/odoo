odoo.define('website_sale_stock.website_sale_stock', function(require) {
    "use strict";
    var core = require('web.core');
    var _t = core._t;
    $(document).ready(function() {
        $('input.js_check_stock, input.product_id').change(function(e) {
            var $product_id = $('input.product_id');
            if (!$product_id.length)
                $product_id = $('.js_product').find('input.js_product_change:checked');
            var variant_stock = $('input[name="product_stock"]').data('stock');
            if (!variant_stock)
                return;
            var available_qty = variant_stock[$product_id.val()];
            var msg = '';
                $('a#add_to_cart').removeClass('disabled');
            if (!available_qty && !_.isUndefined(available_qty)) {
                msg = _t('Sorry ! This product is out of stock');
                $('a#add_to_cart').addClass('disabled');
            } else if (available_qty > 0 && parseInt($('input[name="add_qty"]').val()) > available_qty) {
                msg = _t(_.str.sprintf('Sorry ! Only %s units are still in stock', available_qty));
                $('input[name="add_qty"]').val(available_qty);
            }
            $('div.product_price').parent().find('#stock_warning').remove();
            if (msg) {
                $('div.product_price').after(_.str.sprintf('<p class="%s" style="padding: 15px;" id="stock_warning"> %s </p>', available_qty ? 'bg-warning' : 'bg-danger', msg ));
            }
        })
    })
});
