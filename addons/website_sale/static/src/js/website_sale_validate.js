$(document).ready(function () {

    var _poll_nbr = 0;

    function payment_transaction_poll_status() {
        var order_node = $('div.oe_website_sale_tx_status');
        if (! order_node || order_node.data('orderId') === undefined) {
            return;
        }
        var order_id = order_node.data('orderId');
        return openerp.jsonRpc('/shop/payment/get_status/' + order_id, 'call', {
        }).then(function (result) {
            var tx_node = $('div.oe_website_sale_tx_status');
            var txt = '<h3>Your transaction is waiting confirmation.</h3>';
            _poll_nbr += 1;
            if (result.state == 'pending' && _poll_nbr <= 5) {
                txt = "<h3>Your transaction is waiting confirmation.</h3>";
                setTimeout(function () {
                    payment_transaction_poll_status();
                }, 1000);
            }
            else if (result.state == 'done') {
                txt = "<h3>Your payment has been received.</h3>";
            }
            else if (result.state == 'pending') {
                txt = "<h3>Your transaction is waiting confirmation. You may try to refresh this page.</h3>";
            }
            else if (result.state == 'cancel') {
                txt =  "<h3>The payment seems to have been canceled.</h3>";
            }
            tx_node.html(txt);
        });
    }

    payment_transaction_poll_status();
});
