odoo.define('pos_reataurant.tour.synchronized_table_management', function (require) {
    "use strict";

    var Tour = require("web_tour.tour");

    var qr_code = 'data:image/jpeg;base64,VBORw0KGgoAAAANSUhEUgAAAV4AAAFeCAIAAABCSeBNAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAFlklEQVR4nO3dwW4TMRhGUVrx/o9csauCdDc2ePgdztkXTTzRVTYf/vj6+voB8LvPf/0AwETSAARpAII0AEEagCANQJAGIEgDEKQBCNIABGkAgjQAQRqAIA1AkAYgSAMQfm78zeenoGy68T/OWXrd5z6gb922vZfiuIEgDUCQBiBIAxCkAQjSAARpAII0AEEagCANQJAGIEgDEKQBCNIAhJ1R9pIbZ8hLhoyFz02nb3yDNz7zkge+dSO+1sA00gAEaQCCNABBGoAgDUCQBiBIAxCkAQjSAARpAII0AEEagCANQDg+yl4yZOA8ZNJ7bmftnF85jTTiUIBppAEI0gAEaQCCNABBGoAgDUCQBiBIAxCkAQjSAARpAII0AEEagDBrlM2rczvrc/vfIQNn/pwXCQRpAII0AEEagCANQJAGIEgDEKQBCNIABGkAgjQAQRqAIA1AkAYgSAMQpAEI0gAEaQCCNABBGoAgDUCQBiBIAxCkAQjSAARpAII0AEEagCANQJh1U/a5G5x5de5a7Rvf4I3P/AC/GoAgDUCQBiBIAxCkAQjSAARpAII0AEEagCANQJAGIEgDEKQBCNIAhOOj7KX9L6/OTafPvZRzz3zuMUhOEAjSAARpAII0AEEagCANQJAGIEgDEKQBCNIABGkAgjQAQRqAIA1A2Bllu1n4vzJkZ+1b9zC/GoAgDUCQBiBIAxCkAQjSAARpAII0AEEagCANQJAGIEgDEKQBCNIAhJ1R9pBriIfcDc2rIec8ZME9ZM++Z8SLBKaRBiBIAxCkAQjSAARpAII0AEEagCANQJAGIEgDEKQBCNIABGkAws4oe8m5qem5/e+QeeyQgfOSIUe35Nx0+sbT+Hbflw94gDQAQRqAIA1AkAYgSAMQpAEI0gAEaQCCNABBGoAgDUCQBiBIAxB2Rtk3Tk2HXKs95OjOncaQIfmQc776NEY8OjCNNABBGoAgDUCQBiBIAxCkAQjSAARpAII0AEEagCANQJAGIEgDEI7flL3k3J3Fb7+zPscHHPgvPzD39qsBCNIABGkAgjQAQRqAIA1AkAYgSAMQpAEI0gAEaQCCNABBGoAgDUCYNcpeMmRnfW5IPsSQD3jjYP+cB75I9x0K8ABpAII0AEEagCANQJAGIEgDEKQBCNIABGkAgjQAQRqAIA1AkAYgzBpl37hZvvGZb5whLxmy4L56Gz7raYAhpAEI0gAEaQCCNABBGoAgDUCQBiBIAxCkAQjSAARpAII0AEEagPCxsSmeth69yJD97xKv+3Z73w1vHQjSAARpAII0AEEagCANQJAGIEgDEKQBCNIABGkAgjQAQRqAIA1AOH5T9o0XSS+5cbM85LrnIUPyIR9wyNF9u+9rDTxAGoAgDUCQBiBIAxCkAQjSAARpAII0AEEagCANQJAGIEgDEKQBCMdH2UuGDJxvHJIPGQufc+4xhnzAaQvuEYcCTCMNQJAGIEgDEKQBCNIABGkAgjQAQRqAIA1AkAYgSAMQpAEI0gCEWaNsXr39RdJLhizlb1xw7xnxOYFppAEI0gAEaQCCNABBGoAgDUCQBiBIAxCkAQjSAARpAII0AEEagGCUPdcDtyH/9cc4Z8hjDLnP2k3ZwL8hDUCQBiBIAxCkAQjSAARpAII0AEEagCANQJAGIEgDEKQBCNIAhFmj7CG3Ib+9Gxfcb//MQzb43/xqAII0AEEagCANQJAGIEgDEKQBCNIABGkAgjQAQRqAIA1AkAYgSAMQPjbWnUPuLL7RuZXuOTcu5YcMnK9+gyMeHZhGGoAgDUCQBiBIAxCkAQjSAARpAII0AEEagCANQJAGIEgDEKQBCDujbODt+dUABGkAgjQAQRqAIA1AkAYgSAMQpAEI0gAEaQCCNABBGoAgDUC'

    function verify_order_total(total_str) {
        return [{
            content: 'order total contains ' + total_str,
            trigger: '.order .total .value:contains("' + total_str + '")',
            run: function () {}, // it's a check
        }];
    }

    function verify_sync() {
        return [{
            content: "verify that the order is being sent to the backend",
            trigger: ".js_connecting:visible",
            run: function () {}, // it's a check
        }, {
            content: "verify that the order has been succesfully sent to the backend",
            trigger: ".js_connected:visible",
            run: function () {}, // it's a check
        }];
    }

    function verify_orders_synced(order_count) {
        return [{
            content: "check synced",
            trigger: ".order-sequence",
            run: function() {
                var orders = $('.order-sequence');
                if (orders.length === order_count) {
                    var fail = orders.toArray().some(function(order){
                        return !order.firstChild.data.includes('S-');
                    });
                    if (fail) {
                        throw "sync failed";
                    }
                } else {
                    throw "sync failed";
                }
            },
        }];
    }

    function add_product_to_order(product_name) {
        return [{
            content: 'buy ' + product_name,
            trigger: '.product-list .product-name:contains("' + product_name + '")',
        }, {
            content: 'the ' + product_name + ' have been added to the order',
            trigger: '.order .product-name:contains("' + product_name + '")',
            run: function () {}, // it's a check
        }];
    }

    function generate_keypad_steps(amount_str, keypad_selector) {
        var i, steps = [], current_char;
        for (i = 0; i < amount_str.length; ++i) {
            current_char = amount_str[i];
            steps.push({
                content: 'press ' + current_char + ' on payment keypad',
                trigger: keypad_selector + ' .input-button:contains("' + current_char + '"):visible'
            });
        }

        return steps;
    }

    function generate_payment_screen_keypad_steps(amount_str) {
        return generate_keypad_steps(amount_str, '.payment-numpad');
    }

    function generate_product_screen_keypad_steps(amount_str) {
        return generate_keypad_steps(amount_str, '.numpad');
    }

    function goto_payment_screen_and_select_ipaymu() {
        return [{
            content: "go to payment screen",
            trigger: '.button.pay',
        }, {
            content: "pay with cash",
            trigger: '.paymentmethod:contains("IPaymu")',
        }];
    }

    function open_table(table_id, order_count) {
        order_count = order_count || null;
        var steps = [{
            content: 'open table ' + table_id,
            trigger: '.label:contains(' + table_id +')',
            run: 'click',
        }];
        steps = steps.concat(verify_sync());
        if (order_count !== null){
            steps = steps.concat(verify_orders_synced(order_count));
        }
        return steps;
    }

    function finish_order() {
        var steps = [{
            content: "validate the order",
            trigger: '.button.next:visible',
        }];
        steps = steps.concat(verify_sync());
        steps = steps.concat([{
            content: "next order",
            trigger: '.button.next:visible',
            run: 'click',
        }]);
        return steps;
    }

    var steps = [{
        content: 'waiting for loading to finish',
        trigger: 'body:has(.loader:hidden)',
        run: function () {}, // it's a check
    }]

    steps = steps.concat(add_product_to_order('Office Chair Black'));
    steps = steps.concat(verify_order_total('12.50'));
    steps = steps.concat(goto_payment_screen_and_select_ipaymu());
    steps = steps.concat([{
        content:"Check if total due is outomatically tendered",
        trigger:'.col-tendered:contains("12.50")',
        run: function () {}, // it's a check
    }, {
        content: "Check on payment status text",
        trigger: '.electronic_payment td:contains("Payment request pending")',
        run: function () {}, // it's a check
    }, {
        content: "Send payment request to API",
        trigger: '.button.send_payment_request:visible',
        run: 'click',
    }, {
        content: "Validate order should not work",
        trigger: '.button.next',
        run: 'click',
    }, {
        content: "Payment screen should be still visible",
        trigger: '.payment-screen:visible',
        run: function () {}, // it's a check
    },{
        content: "Check qr code visible",
        trigger: '.payment-qr-code img[src*="' + qr_code + '"]',
        run: function () {}, // it's a check
    },{
        content: "Check payment status",
        trigger: '.paymentline.electronic_payment td:first:contains("Waiting for payment")',
        run: function () {}, // it's a check
    },{
        content: "Check payment gets done (this is mocked)",
        trigger: '.paymentline.electronic_payment td:first:contains("Payment Successful")',
        run: function () {}, // it's a check
    }, {
        content: "Validate order",
        trigger: '.button.next',
        run: 'click',
    }, {
        content: "",
        trigger: '.receipt-screen:visible',
        run: function () {}, // it's a check
    }])
    Tour.register('pos_ipaymu', { test: true, url: '/pos/web' }, steps);
});
