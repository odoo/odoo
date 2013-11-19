$(document).ready(function () {

    var _poll_nbr = 0;

    function payment_transaction_poll_status() {
        return openerp.jsonRpc('/shop/payment/transaction/get_status', 'call', {
        }).then(function (result) {
            _poll_nbr += 1;
            if (result.state == 'done') {
                $('div.oe_website_sale_confirmation').html(function() {
                    return "<h2>Thanks for your order</h2>";
                });
            }
            else if (result.state == 'pending') {
                if (_poll_nbr <= 10) {
                    $('div.oe_website_sale_confirmation').html(function() {
                        return "<h2>Waiting validation ...</h2>";
                    });
                    setTimeout(function () {
                        return payment_transaction_poll_status();
                    }, 1000);
                }
                else {
                    $('div.oe_website_sale_confirmation').html(function() {
                        return "<h2>You payment is currently under review. Please come back later.</h2>";
                    });
                }
            }
            else if (result.state == 'cancel') {
                $('div.oe_website_sale_confirmation').html(function() {
                    return "<h2>The payment seems to have been canceled.</h2>";
                });   
            }
        });
    }

    payment_transaction_poll_status();
});
