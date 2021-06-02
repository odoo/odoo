odoo.define('pos_reataurant.tour.synchronized_table_management', function (require) {
    "use strict";

    var Tour = require("web_tour.tour");

    function verify_order_total(total_str) {
        return [{
            content: 'order total contains ' + total_str,
            trigger: '.order .total .value:contains("' + total_str + '")',
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
                    return
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

    function goto_payment_screen_and_select_payment_method() {
        return [{
            content: "go to payment screen",
            trigger: '.button.pay',
        }, {
            content: "pay with cash",
            trigger: '.paymentmethod:contains("Cash")',
        }];
    }

    function open_table(table_id, order_count) {
        order_count = order_count || null;
        var steps = [{
            content: 'open table ' + table_id,
            trigger: '.label:contains(' + table_id +')',
            run: 'click',
        }];
        if (order_count !== null){
            steps = steps.concat(verify_orders_synced(order_count));
        }
        return steps;
    }

    function transfer_order_to_table(table_id, order_uid) {
        return [{
            content: 'Click transfer button',
            trigger: '.control-button:contains("Transfer")',
            run: 'click',
        }, {
            content: 'Transfer order to table ' + table_id,
            trigger: '.label:contains(' + table_id +')',
            run: 'click',
        }, {
            content: 'Check if order ' + order_uid + ' is open after transfer',
            trigger: '.order-button.selected .order-sequence:contains("' + order_uid + '")',
            run: function(){} // Check
        }];
    }

    function finish_order() {
        var steps = [{
            content: "validate the order",
            trigger: '.button.next:visible',
        }];
        steps = steps.concat([{
            content: "next order",
            trigger: '.button.next:visible',
        }]);
        return steps;
    }

    /* pos_restaurant_sync
     *
     * Run on new session.
     */
    var steps = [{
        content: 'waiting for loading to finish',
        trigger: 'body:has(.loader:hidden)',
        run: function () {},
    }]


    steps = steps.concat(open_table('T5'));

    steps = steps.concat(add_product_to_order('Coca-Cola'));
    steps = steps.concat(add_product_to_order('Water'));
    steps = steps.concat(verify_order_total('4.40'));
    steps = steps.concat([{
        content: 'start new order',
        trigger: '.neworder-button',
        run: 'click',
    }]);
    steps = steps.concat(add_product_to_order('Coca-Cola'));
    steps = steps.concat(add_product_to_order('Minute Maid'));
    steps = steps.concat(verify_order_total('4.40'));
    steps = steps.concat(goto_payment_screen_and_select_payment_method());
    steps = steps.concat(generate_payment_screen_keypad_steps('6.05'));
    steps = steps.concat(finish_order());
    steps = steps.concat(open_table('T5', 1));
    steps = steps.concat(verify_order_total('4.40'));
    steps = steps.concat([{
        content: 'start new order',
        trigger: '.neworder-button',
        run: 'click',
    }]);
    steps = steps.concat(add_product_to_order('Coca-Cola'));
    steps = steps.concat(add_product_to_order('Minute Maid'));
    steps = steps.concat([{
        content: 'back to floor',
        trigger: '.floor-button',
        run: 'click',
    }]);
    steps = steps.concat(open_table('T5', 2));
    steps = steps.concat([{
        content: 'delete order',
        trigger: '.deleteorder-button',
        run: 'click',
    }, {
        content: 'confirm delete',
        trigger: '.button.confirm',
        run: 'click',
    }, {
        content: 'back to floor',
        trigger: '.floor-button',
        run: 'click',
    }]);
    steps = steps.concat(open_table('T5', 1));

    Tour.register('pos_restaurant_sync', { test: true, url: '/pos/web' }, steps);


    /* pos_restaurant_sync_second_login
     *
     * This tour should be run after the first tour is done.
     */
    var steps = [{
        content: 'waiting for loading to finish',
        trigger: 'body:has(.loader:hidden)',
        run: function () {},
    }];
    steps = steps.concat(open_table('T5', 1));
    steps = steps.concat(verify_order_total('4.40'));
    
    // Test transfering an order
    steps = steps.concat(transfer_order_to_table('T4', '002-0001'));

    // Test if products still get merged after transfering the order
    steps = steps.concat(add_product_to_order('Coca-Cola'));
    steps = steps.concat({
        content: 'check the order-line for Coca-Cola has 2 Units',
        trigger: '.orderlines:has(.orderline .product-name:contains("Coca-Cola")) .info-list:contains("2.000")',
        run: function () {},
    })
    steps = steps.concat(generate_product_screen_keypad_steps('1'));

    steps = steps.concat(goto_payment_screen_and_select_payment_method());
    steps = steps.concat(generate_payment_screen_keypad_steps('4.4'));
    steps = steps.concat(finish_order());
    steps = steps.concat(open_table('T2'));

    // Test transfering an empty order
    steps = steps.concat(transfer_order_to_table('T4', '2'));

    steps = steps.concat(add_product_to_order('Coca-Cola'));
    steps = steps.concat(verify_order_total('2.20'));

    // Take a synced order with products, remove the products 
    // and check if the order is still available in the front-end
    steps = steps.concat([{
        content: 'back to floor',
        trigger: '.floor-button',
        run: 'click',
    }]);
    steps = steps.concat(open_table('T4', 1));
    steps = steps.concat([{
        content: 'click backspace to set quantity to 0',
        trigger: '.numpad-backspace',
        run: 'click',
    }, {
        content: 'click backspace to remove line',
        trigger: '.numpad-backspace',
        run: 'click',
    }]);
    steps = steps.concat([{
        content: 'back to floor',
        trigger: '.floor-button',
        run: 'click',
    }]);
    steps = steps.concat(open_table('T4', 1));
    steps = steps.concat(add_product_to_order('Coca-Cola'));
    steps = steps.concat(verify_order_total('2.20'));
    steps = steps.concat([{
        content: 'back to floor',
        trigger: '.floor-button',
        run: 'click',
    }]);

    Tour.register('pos_restaurant_sync_second_login', { test: true, url: '/pos/web' }, steps);

});
