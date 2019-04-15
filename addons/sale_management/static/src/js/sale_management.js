odoo.define('sale_management.sale_management', function (require) {
'use strict';

require('web.dom_ready');
var ajax = require('web.ajax');
var Widget = require('web.Widget');

if (!$('.o_portal_sale_sidebar').length) {
    return $.Deferred().reject("DOM doesn't contain '.o_portal_sale_sidebar'");
}

    // Add to SO button
    var UpdateLineButton = Widget.extend({
        events: {
            'click' : 'onClick',
        },
        onClick: function (ev) {
            ev.preventDefault();
            var self = this;
            var href = this.$el.attr("href");
            var order_id = href.match(/my\/orders\/(?<order_id>[0-9]+)/).groups.order_id;
            var line_id = href.match(/update_line(_dict)?\/(?<line_id>[0-9]+)/).groups.line_id;
            var params = {
                'line_id': line_id,
                'remove': self.$el.is('[href*="remove"]'),
                'unlink': self.$el.is('[href*="unlink"]'),
            };
            var matched = href.match(/token=(?<token>[\w\d-]*)/);
            if (matched.groups.token) {
                params.access_token = matched.groups.token;
            }
            var url = "/my/orders/" + parseInt(order_id) + "/update_line_dict";
            ajax.jsonRpc(url, 'call', params).then(function (data) {
                if (!data) {
                    window.location.reload();
                }
                self.$el.parents('.input-group:first').find('.js_quantity').val(data.order_line_product_uom_qty);
                var $priceTotal = self.$el.parents('tr:first').find('.oe_order_line_price_total .oe_currency_value');
                var $priceSubTotal = self.$el.parents('tr:first').find('.oe_order_line_price_subtotal .oe_currency_value');
                if ($priceTotal && data.order_line_price_total) {
                    $priceTotal.text(data.order_line_price_total);
                }
                if ($priceSubTotal && data.order_line_price_subtotal) {
                    $priceSubTotal.text(data.order_line_price_subtotal);
                }
                if (data.order_amount_total) {
                    $('[data-id="total_amount"]>span').text(data.order_amount_total);
                }
            });
            return false;
        },
    });

    var update_button_list = [];
    $('a.js_update_line_json').each(function (index) {
        var button = new UpdateLineButton();
        button.setElement($(this)).start();
        update_button_list.push(button);
    });

});
