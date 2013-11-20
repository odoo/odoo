$(document).ready(function () {

    var _poll_nbr = 0;

    function payment_transaction_validate() {
        return openerp.jsonRpc('/shop/payment/validate', 'call', {});
    }

    function payment_transaction_poll_status() {
        return openerp.jsonRpc('/shop/payment/confirm', 'call', {
        }).done(function (result) {
            // console.log('--done', result);
            _poll_nbr += 1;
            if (result.state == 'done') {
                $('div.oe_website_sale_confirmation').html(function() {
                    return "<h2>Thanks for your order</h2>";
                });
            }
            else if (result.state == 'pending') {
                if (_poll_nbr <= 2) {
                    $('div.oe_website_sale_confirmation').html(function() {
                        return "<h2>Waiting validation ...</h2>";
                    });
                    setTimeout(function () {
                        return inner_done = payment_transaction_poll_status();
                    }, 1000);
                    // return inner_done;
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

    payment_transaction_poll_status().done(function (result) {
        // console.log('finished', result);
        payment_transaction_validate();
    });
});
