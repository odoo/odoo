// Модальное окно выбора вариантов товара полностью удалено, функционал перенесён на обычную страницу.

odoo.define('multi_vendor_marketplace.buy_now_button', function (require) {
    'use strict';
    
    var publicWidget = require('web.public.widget');
    
    publicWidget.registry.BuyNowButton = publicWidget.Widget.extend({
        selector: '.oe_website_sale',
        events: {
            'click .o_we_buy_now': '_onBuyNowClick',
        },
        _onBuyNowClick: function (ev) {
            var $btn = $(ev.currentTarget);
            var $form = $btn.closest('form');
            if ($form.length) {
                // Add express=1 if not present
                if ($form.find('input[name="express"]').length === 0) {
                    $('<input>').attr({type: 'hidden', name: 'express', value: '1'}).appendTo($form);
                }
                $form.submit();
            }
        }
    });
});

// Quantity control for product detail page
odoo.define('multi_vendor_marketplace.product_qty_control', function (require) {
    $(document).ready(function () {
        $(document).on('click', '.js_add_qty', function () {
            var $input = $(this).closest('.input-group').find('.js_quantity');
            var val = parseInt($input.val()) || 1;
            $input.val(val + 1).trigger('change');
        });
        $(document).on('click', '.js_remove_qty', function () {
            var $input = $(this).closest('.input-group').find('.js_quantity');
            var val = parseInt($input.val()) || 1;
            if (val > 1) {
                $input.val(val - 1).trigger('change');
            }
        });
    });
}); 