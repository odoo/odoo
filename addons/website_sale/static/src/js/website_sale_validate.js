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
            if(result.recall) {
                if (_poll_nbr < 20){
                    setTimeout(function () { payment_transaction_poll_status(); }, Math.ceil(_poll_nbr / 3) * 1000);
                }
                else {
                    var $message = $(result.message);
                    $message.find('span:first').prepend($(
                        "<i title='We are waiting the confirmation of the bank or payment provider' class='fa fa-warning' style='margin-right:10px;'>"));
                    result.message = $message.html();
                }
            }
            $('div.oe_website_sale_tx_status').html(result.message);
        });
    }

    payment_transaction_poll_status();
});

});
