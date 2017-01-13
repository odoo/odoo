odoo.define('website_sale.validate', function(require) {
"use strict";

var ajax = require('web.ajax');

$(document).ready(function () {

    var _poll_nbr = 0;

    function payment_transaction_poll_status() {
        var order_node = $('div.oe_website_sale_tx_status');
        if (! order_node || order_node.data('order-id') === undefined) {
            return;
        }
        var order_id = order_node.data('order-id');
        return ajax.jsonRpc('/shop/payment/get_status/' + order_id, 'call', {
        }).then(function (result) {
            _poll_nbr += 1;
            if(result.recall && _poll_nbr <= 5){
                setTimeout(function () { payment_transaction_poll_status(); }, 1000);
            }
            $('div.oe_website_sale_tx_status').html(result.message);
        });
    }

    payment_transaction_poll_status();
});

});
