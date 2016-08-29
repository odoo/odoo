odoo.define('point_of_sale.Tour', function (require) {
    "use strict";

    var Tour = require('web.Tour');

    function add_product_to_order(product_name) {
        return [{
            title: 'buy ' + product_name,
            element: '.product-list .product-name:contains("' + product_name + '")',
        }, {
            title: 'the ' + product_name + ' have been added to the order',
            waitFor: '.order .product-name:contains("' + product_name + '")',
        }];
    }

    function generate_keypad_steps(amount_str, keypad_selector) {
        var i, steps = [], current_char;
        for (i = 0; i < amount_str.length; ++i) {
            current_char = amount_str[i];
            steps.push({
                title: 'press ' + current_char + ' on payment keypad',
                element: keypad_selector + ' .input-button:contains("' + current_char + '"):visible'
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

    function verify_order_total(total_str) {
        return [{
            title: 'order total contains ' + total_str,
            waitFor: '.order .total .value:contains("' + total_str + '")',
        }];
    }

    function goto_payment_screen_and_select_payment_method() {
        return [{
            title: "go to payment screen",
            element: '.button.pay',
        }, {
            title: "pay with cash",
            element: '.paymentmethod:contains("Cash")',
        }];
    }

    function finish_order() {
        return [{
            title: "validate the order",
            element: '.button.next:visible',
        }, {
            title: "verify that the order is being sent to the backend",
            waitFor: ".js_connecting:visible",
        }, {
            title: "verify that the order has been succesfully sent to the backend",
            waitFor: ".js_connected:visible",
        }, {
            title: "next order",
            element: '.button.next:visible',
        }];
    }

    var steps = [{
            title: 'wait for loading screen',
            waitFor: '.loader'
        }, {
            title: 'waiting for loading to finish',
            waitFor: '.loader:hidden',
        }];

    steps = steps.concat(add_product_to_order('Peaches'));
    steps = steps.concat(verify_order_total('5.10'));

    steps = steps.concat(add_product_to_order('Peaches')); // buy another kg of peaches
    steps = steps.concat(verify_order_total('10.20'));
    steps = steps.concat(goto_payment_screen_and_select_payment_method());
    steps = steps.concat(generate_payment_screen_keypad_steps("12.20"));

    steps = steps.concat([{
        title: "verify tendered",
        waitFor: '.col-tendered:contains("12.20")',
    }, {
        title: "verify change",
        waitFor: '.col-change:contains("2.00")',
    }]);

    steps = steps.concat(finish_order());

    // test opw-672118 orderline subtotal rounding
    steps = steps.concat(add_product_to_order('Peaches'));
    steps = steps.concat(generate_product_screen_keypad_steps('.999')); // sets orderline qty
    steps = steps.concat(verify_order_total('5.09'));
    steps = steps.concat(goto_payment_screen_and_select_payment_method());
    steps = steps.concat(generate_payment_screen_keypad_steps("10"));
    steps = steps.concat(finish_order());

    steps = steps.concat([{
        title: "close the Point of Sale frontend",
        element: ".header-button",
    }, {
        title: "confirm closing the frontend",
        element: ".header-button",
    }]);

    Tour.register({
        id: 'pos_basic_order',
        name: 'Complete a basic order trough the Front-End',
        path: '/pos/web',
        steps: steps,
    });

});
