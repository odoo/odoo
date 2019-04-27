odoo.define('sale_management.sale_management', function (require) {
'use strict';

var publicWidget = require('web.public.widget');

publicWidget.registry.SaleUpdateLineButton = publicWidget.Widget.extend({
    selector: '.o_portal_sale_sidebar a.js_update_line_json',
    events: {
        'click': '_onClick',
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClick: function (ev) {
        ev.preventDefault();
        var self = this;
        var href = this.$el.attr("href");
        var orderID = href.match(/my\/orders\/([0-9]+)/);
        var lineID = href.match(/update_line\/([0-9]+)/);
        var params = {
            'line_id': lineID[1],
            'remove': self.$el.is('[href*="remove"]'),
            'unlink': self.$el.is('[href*="unlink"]'),
        };
        var token = href.match(/token=(.*)/);
        if (token) {
            params['access_token'] = token;
        }
        var url = "/my/orders/" + parseInt(orderID[1]) + "/update_line";
        this._rpc({
            route: url,
            params: params,
        }).then(function (data) {
            if (!data) {
                window.location.reload();
            }
            self.$el.closest('.input-group').find('.js_quantity').val(data[0]);
            $('[data-id="total_amount"] > span').html(data[1]);
        });
    },
});
});
