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
            var order_id = href.match(/my\/orders\/([0-9]+)/);
            var line_id = href.match(/update_line\/([0-9]+)/);
            var params = {
                'line_id': line_id[1],
                'remove': self.$el.is('[href*="remove"]'),
                'unlink': self.$el.is('[href*="unlink"]'),
            };
            var token = href.match(/token=(.*)/);
            if (token) {
                params.access_token = token;
            }
            var url = "/my/orders/" + parseInt(order_id[1]) + "/update_line";
            ajax.jsonRpc(url, 'call', params).then(function (data) {
                if (!data) {
                    window.location.reload();
                }
                self.$el.parents('.input-group:first').find('.js_quantity').val(data[0]);
                $('[data-id="total_amount"]>span').html(data[1]);
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
