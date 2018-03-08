odoo.define('website_quote.website_quote', function (require) {
'use strict';

var ajax = require('web.ajax');
var SalePortalSidebar = require('sale.SalePortalSidebar');


SalePortalSidebar.include({
    events: _.extend({}, SalePortalSidebar.prototype.events, {
        'click a.js_update_line_json': '_onClickUpdateOrderLine',
    }),

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickUpdateOrderLine: function (ev) {
        ev.preventDefault();
        var self = this,
            $currentTarget = $(ev.currentTarget),
            href = $currentTarget.attr('href'),
            orderID = href.match(/order_id=([0-9]+)/),
            lineID = href.match(/update_line\/([0-9]+)/),
            token = href.match(/token=(.*)/);

        ajax.jsonRpc("/quote/update_line", 'call', {
            'line_id': lineID[1],
            'order_id': parseInt(orderID[1]),
            'token': token[1],
            'remove': $currentTarget.is('[href*="remove"]'),
            'unlink': $currentTarget.is('[href*="unlink"]')
        }).then(function (data) {
            if (!data) {
                window.location.reload();
            }
            $currentTarget.parents('.input-group:first').find('.js_quantity').val(data['qty']);
            self.$el.find('[data-id="total_amount"]>span').html(data['amount']);
            self.$el.find(".o_validity_date").first().before(data['portal_order_expire_detail']).end().remove();
            self.$el.find(".js_update_order_amount").first().before(data['portal_order_amount_detail']).end().remove();
            // reload iframe content, due to updated order line
            self.printContent = false;
        });
        return false;
    },
});
});
