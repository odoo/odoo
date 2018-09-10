odoo.define('point_of_sale.Tour', function (require) {
    "use strict";

    var tour = require("web_tour.tour");

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

    function verify_order_total(total_str) {
        return [{
            content: 'order total contains ' + total_str,
            trigger: '.order .total .value:contains("' + total_str + '")',
            run: function () {}, // it's a check
        }];
    }

    function goto_payment_screen_and_select_payment_method() {
        return [{
            content: "go to payment screen",
            trigger: '.button.pay',
        }, {
            content: "pay with cash",
            trigger: '.paymentmethod:contains("Cash")',
        }];
    }

    function finish_order() {
        return [{
            content: "validate the order",
            trigger: '.button.next:visible',
        }, {
            content: "verify that the order is being sent to the backend",
            trigger: ".js_connecting:visible",
            run: function () {}, // it's a check
        }, {
            content: "verify that the order has been succesfully sent to the backend",
            trigger: ".js_connected:visible",
            run: function () {}, // it's a check
        }, {
            content: "next order",
            trigger: '.button.next:visible',
        }];
    }

    var steps = [{
            content: 'waiting for loading to finish',
            trigger: '.o_main_content:has(.loader:hidden)',
            run: function () {}, // it's a check
        }];

    steps = steps.concat(add_product_to_order('Peaches'));
    steps = steps.concat(verify_order_total('5.10'));

    steps = steps.concat(add_product_to_order('Peaches')); // buy another kg of peaches
    steps = steps.concat(verify_order_total('10.20'));
    steps = steps.concat(goto_payment_screen_and_select_payment_method());
    steps = steps.concat(generate_payment_screen_keypad_steps("12.20"));

    steps = steps.concat([{
        content: "verify tendered",
        trigger: '.col-tendered:contains("12.20")',
        run: function () {}, // it's a check
    }, {
        content: "verify change",
        trigger: '.col-change:contains("2.00")',
        run: function () {}, // it's a check
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
        content: "close the Point of Sale frontend",
        trigger: ".header-button",
    }, {
        content: "confirm closing the frontend",
        trigger: ".header-button.confirm",
        run: function() {}, //it's a check,
    }]);

    tour.register('pos_basic_order', { test: true, url: '/pos/web' }, steps);

});
