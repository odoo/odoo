odoo.define('pos_discount.tour.global_discount', function (require) {
    "use strict";

    var Tour = require("web_tour.tour");

    function assert (condition, message) {
        if (! condition) {
            throw message || "Assertion failed";
        }
    }

    function verify_order_total(total_str) {
        return [{
            content: 'order total contains ' + total_str,
            trigger: '.order .total .value:contains("' + total_str + '")',
            run: function () {}, // it's a check
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

    function generate_popup_keypad_steps(amount_str) {
        steps = generate_keypad_steps(amount_str, '.popup-numpad');
        return steps.concat ([{
            content: "close popup keypad",
            trigger: ".confirm:visible"
        }]);
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

    var steps = [{
        content: 'waiting for loading to finish',
        trigger: 'body:has(.loader:hidden)',
        run: function () {},
    }]
    steps = steps.concat([{
        content: 'all products',
        trigger: '.fa-home',
        run: 'click'
    }]);

    // Select 2 products with different tax on them and check that adding discount takes 
    // the tax in concideration.
    //
    // Apply a discount on the order of 10.5 %
    // 
    // ------------------------------------------------------------
    // | Product               | Price excl. | Tax % | Price incl.|
    // ------------------------|-------------|-------|------------|
    // | Acoustic Bloc Screens | 2950.00     | 15    | 3392.50    |
    // | Monitor Stand         | 3.19        | 10    | 3.51       |
    // | Discount              | -309.75     | 15    | -356.21    |
    // | Discount              | -0.33       | 10    | -0.36      |
    // ------------------------------------------------------------
    // | Total: 3,039.44       |
    // | Taxes: 396.33         |
    // -------------------------

    steps = steps.concat(add_product_to_order('Acoustic Bloc Screen'));
    steps = steps.concat(add_product_to_order('Monitor Stand'));
    steps = steps.concat(verify_order_total('3,396.01'));
    steps = steps.concat([{
        content: 'open discount screen',
        trigger: '.js_discount',
        run: 'click',
    }]);
    steps = steps.concat(generate_popup_keypad_steps('10.5'));
    steps = steps.concat(verify_order_total('3,039.44'));

    // Add a 3th product with another tax and and add to one of the already ordered products. 
    // The amount of discount should automatically be recomputed.
    //
    // ---------------------------------------------------------------------
    // | Product               | Amount | Price excl. | Tax % | Price incl.|
    // ------------------------|--------|-------------|-------|------------|
    // | Acoustic Bloc Screens | 1      | 2950.00     | 15    | 3392.50    |
    // | Monitor Stand         | 2      | 6.38        | 10    | 7.02       |
    // | Desk Organizer        | 1      | 5.10        | 0     | 5.10       |
    // | Discount              |        | -309.75     | 15    | -356.21    |
    // | Discount              |        | -0.67       | 10    | -0.72      |
    // | Discount              |        | -0.54       | 0     | -0.54      |
    // ---------------------------------------------------------------------
    // | Total: 3,047.13       |
    // | Taxes: 396.61         |
    // -------------------------

    steps = steps.concat(add_product_to_order('Monitor Stand'));
    steps = steps.concat(add_product_to_order('Desk Organizer'));
    steps = steps.concat(verify_order_total('3,047.13'));

    // The Discount is automatically computed, for this reason discount lines should never be 
    // selected, instead they should be controlled by the "Discount" button. if the button is 
    // green a discount is applied.

    steps = steps.concat([{
        content: 'Check discount is selected and has 3 lines',
        trigger: '.js_discount.discount_selected',
        run: function() {
            assert(3 === $('.orderline .product-name:contains("Discount")').length,
                "There should be 3 discount lines")
        }
    }, {
        content: 'open discount screen to remove discount',
        trigger: '.js_discount',
        run: 'click',
    }]);
    steps = steps.concat(generate_popup_keypad_steps('0'));
    steps = steps.concat([{
        content: 'Check discount is not selected',
        trigger: '.js_discount:not(.discount_selected)',
        run: function() {
            assert(0 === $('.orderline .product-name:contains("Discount")').length,
                "There should be 0 discount lines")
        }
    }]);
    steps = steps.concat(verify_order_total('3,404.62'));
    
    // If the barcode of the Discount product is scanned, the discount popup should be shown.

    steps = steps.concat([{
        content: 'Fill barcode buffer with discount barcode',
        trigger: 'body',
        run: function() {
            $('input.ean').val("123456");
        },
    }, {
        content: 'Trigger barcode action',
        trigger: '.button.barcode',
        run: 'click'
    }]);
    steps = steps.concat(generate_popup_keypad_steps('10.5'));
    steps = steps.concat([{
        content: 'Check discount is selected',
        trigger: '.js_discount.discount_selected',
        run: function() {
            assert(3 === $('.orderline .product-name:contains("Discount")').length,
                "There should be 3 discount lines")
        }
    }]);
    steps = steps.concat(verify_order_total('3,047.13'));

    steps = steps.concat(goto_payment_screen_and_select_payment_method());
    steps = steps.concat(generate_payment_screen_keypad_steps('3047.13'));

    // Validate order and check if the total discount on the ticket is 310.96

    steps = steps.concat([{
        content: "validate the order",
        trigger: '.button.next:visible',
    }, {
        content: 'Check Discount on ticket',
        trigger: '.pos-receipt div:contains("Discounts") span:contains("310.96")',
        run: function() {}
    }, {
        content: "next order",
        trigger: '.button.next:visible',
    }]);

    steps = steps.concat([{
        content: "close the Point of Sale frontend",
        trigger: ".header-button",
        run: 'click'
    }, {
        content: "confirm closing the frontend",
        trigger: ".header-button.confirm",
        run: 'click'
    }]);
    Tour.register('pos_discount_global_discount', { test: true, url: '/pos/web?debug=1' }, steps);
});
