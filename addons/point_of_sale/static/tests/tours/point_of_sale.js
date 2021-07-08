/* global posmodel */
odoo.define('point_of_sale.tour.pricelist', function (require) {
    "use strict";

    var Tour = require('web_tour.tour');
    var rpc = require('web.rpc');
    var utils = require('web.utils');
    var round_di = utils.round_decimals;

    function assert (condition, message) {
        if (! condition) {
            throw message || "Assertion failed";
        }
    }

    function _build_pricelist_context (pricelist, quantity, date) {
        return {
            pricelist: pricelist.id,
            quantity: quantity,
        };
    }

    function compare_backend_frontend (product, pricelist_name, quantity) {
        return function () {
            var pricelist = _.findWhere(posmodel.pricelists, {name: pricelist_name});
            var frontend_price = product.get_price(pricelist, quantity);
            // ORM applies digits= on non-stored computed field when
            // reading. It does not however truncate like it does when
            // storing the field.
            frontend_price = round_di(frontend_price, posmodel.dp['Product Price']);

            var context = _build_pricelist_context(pricelist, quantity);
            return rpc.query({model: 'product.product', method: 'read', args: [[product.id], ['price']], context: context})
                .then(function (backend_result) {
                    var debug_info = _.extend(context, {
                        product: product.id,
                        product_display_name: product.display_name,
                        pricelist_name: pricelist.name,
                    });
                    var backend_price = backend_result[0].price;
                    assert(frontend_price === backend_price,
                           JSON.stringify(debug_info) + ' DOESN\'T MATCH -> ' + backend_price + ' (backend) != ' + frontend_price + ' (frontend)');
                    return Promise.resolve();
                });
        };
    }

    // The global posmodel is only present when the posmodel is instanciated
    // So, wait for everythiong to be loaded
    var steps = [{ // Leave category displayed by default
        content: 'waiting for loading to finish',
        extra_trigger: 'body .pos:not(:has(.loader))', // Pos has finished loading
        trigger: '.o_loading_indicator:not(.o_loading)', // WebClient has finished Loading
        run: function () {
            var product_wall_shelf = posmodel.db.search_product_in_category(0, 'Wall Shelf Unit')[0];
            var product_small_shelf = posmodel.db.search_product_in_category(0, 'Small Shelf')[0];
            var product_magnetic_board = posmodel.db.search_product_in_category(0, 'Magnetic Board')[0];
            var product_monitor_stand = posmodel.db.search_product_in_category(0, 'Monitor Stand')[0];
            var product_desk_pad = posmodel.db.search_product_in_category(0, 'Desk Pad')[0];
            var product_letter_tray = posmodel.db.search_product_in_category(0, 'Letter Tray')[0];
            var product_whiteboard = posmodel.db.search_product_in_category(0, 'Whiteboard')[0];

            compare_backend_frontend(product_letter_tray, 'Public Pricelist', 0, undefined)()
                .then(compare_backend_frontend(product_letter_tray, 'Public Pricelist', 1, undefined))
                .then(compare_backend_frontend(product_letter_tray, 'Fixed', 1, undefined))
                .then(compare_backend_frontend(product_wall_shelf, 'Fixed', 1, undefined))
                .then(compare_backend_frontend(product_small_shelf, 'Fixed', 1, undefined))
                .then(compare_backend_frontend(product_wall_shelf, 'Percentage', 1, undefined))
                .then(compare_backend_frontend(product_small_shelf, 'Percentage', 1, undefined))
                .then(compare_backend_frontend(product_magnetic_board, 'Percentage', 1, undefined))
                .then(compare_backend_frontend(product_wall_shelf, 'Formula', 1, undefined))
                .then(compare_backend_frontend(product_small_shelf, 'Formula', 1, undefined))
                .then(compare_backend_frontend(product_magnetic_board, 'Formula', 1, undefined))
                .then(compare_backend_frontend(product_monitor_stand, 'Formula', 1, undefined))
                .then(compare_backend_frontend(product_desk_pad, 'Formula', 1, undefined))
                .then(compare_backend_frontend(product_wall_shelf, 'min_quantity ordering', 1, undefined))
                .then(compare_backend_frontend(product_wall_shelf, 'min_quantity ordering', 2, undefined))
                .then(compare_backend_frontend(product_letter_tray, 'Category vs no category', 1, undefined))
                .then(compare_backend_frontend(product_letter_tray, 'Category', 1, undefined))
                .then(compare_backend_frontend(product_wall_shelf, 'Product template', 1, undefined))
                .then(compare_backend_frontend(product_wall_shelf, 'Dates', 1, undefined))
                .then(compare_backend_frontend(product_small_shelf, 'Pricelist base rounding', 1, undefined))
                .then(compare_backend_frontend(product_whiteboard, 'Public Pricelist', 1, undefined))
                .then(function () {
                    $('.pos').addClass('done-testing');
                });
        },
    }, {
        trigger: '.opening-cash-control .button:contains("Open session")',
    }];

    steps = steps.concat([{
        content: "wait for unit tests to finish",
        trigger: ".pos.done-testing",
        run: function () {}, // it's a check
    }, {
        content: "click category switch",
        trigger: ".breadcrumb-home",
        run: 'click',
    }, {
        content: "click pricelist button",
        trigger: ".control-button.o_pricelist_button",
    }, {
        content: "verify default pricelist is set",
        trigger: ".selection-item.selected:contains('Public Pricelist')",
        run: function () {}, // it's a check
    }, {
        content: "select fixed pricelist",
        trigger: ".selection-item:contains('Fixed')",
    }, {
        content: "open customer list",
        trigger: "button.set-customer",
    }, {
        content: "select Deco Addict",
        trigger: ".client-line:contains('Deco Addict')",
    }, {
        content: "confirm selection",
        trigger: ".clientlist-screen .next",
    }, {
        content: "click pricelist button",
        trigger: ".control-button.o_pricelist_button",
    }, {
        content: "verify pricelist changed",
        trigger: ".selection-item.selected:contains('Public Pricelist')",
        run: function () {}, // it's a check
    }, {
        content: "cancel pricelist dialog",
        trigger: ".button.cancel:visible",
    }, {
        content: "open customer list",
        trigger: "button.set-customer",
    }, {
        content: "select Lumber Inc",
        trigger: ".client-line:contains('Lumber Inc')",
    },  {
        content: "confirm selection",
        trigger: ".clientlist-screen .next",
    }, {
        content: "click pricelist button",
        trigger: ".control-button.o_pricelist_button",
    }, {
        content: "verify pricelist remained public pricelist ('Not loaded' is not available)",
        trigger: ".selection-item.selected:contains('Public Pricelist')",
        run: function () {}, // it's a check
    }, {
        content: "cancel pricelist dialog",
        trigger: ".button.cancel:visible",
    },  {
        content: "click pricelist button",
        trigger: ".control-button.o_pricelist_button",
    }, {
        content: "select fixed pricelist",
        trigger: ".selection-item:contains('min_quantity ordering')",
    }, {
        content: "order 1 kg shelf",
        trigger: ".product:contains('Wall Shelf')",
    }, {
        content: "change qty to 2 kg",
        trigger: ".numpad button.input-button:visible:contains('2')",
    }, {
        content: "qty of Wall Shelf line should be 2",
        trigger: ".order-container .orderlines .orderline.selected .product-name:contains('Wall Shelf')",
        extra_trigger: ".order-container .orderlines .orderline.selected .product-name:contains('Wall Shelf') ~ .info-list .info em:contains('2.0')",
        run: function() {},
    }, {
        content: "verify that unit price of shelf changed to $1",
        trigger: ".total > .value:contains('$ 2.00')",
        run: function() {},
    }, {
        content: "order different shelf",
        trigger: ".product:contains('Small Shelf')",
    }, {
        content: "Small Shelf line should be selected with quantity 1",
        trigger: ".order-container .orderlines .orderline.selected .product-name:contains('Small Shelf')",
        extra_trigger: ".order-container .orderlines .orderline.selected .product-name:contains('Small Shelf') ~ .info-list .info em:contains('1.0')",
        run: function() {}
    }, {
        content: "change to price mode",
        trigger: ".numpad button:contains('Price')",
    }, {
        content: "make sure price mode is activated",
        trigger: ".numpad button.selected-mode:contains('Price')",
        run: function() {},
    }, {
        content: "manually override the unit price of these shelf to $5",
        trigger: ".numpad button.input-button:visible:contains('5')",
    }, {
        content: "Small Shelf line should be selected with unit price of 5",
        trigger: ".order-container .orderlines .orderline.selected .product-name:contains('Small Shelf')",
        extra_trigger: ".order-container .orderlines .orderline.selected .product-name:contains('Small Shelf') ~ .price:contains('5.0')",
    }, {
        content: "change back to qty mode",
        trigger: ".numpad button:contains('Qty')",
    }, {
        content: "make sure qty mode is activated",
        trigger: ".numpad button.selected-mode:contains('Qty')",
        run: function() {},
    }, {
        content: "click pricelist button",
        trigger: ".control-button.o_pricelist_button",
    }, {
        content: "select public pricelist",
        trigger: ".selection-item:contains('Public Pricelist')",
    }, {
        content: "verify that the boni shelf have been recomputed and the shelf have not (their price was manually overridden)",
        trigger: ".total > .value:contains('$ 8.96')",
    }, {
        content: "click pricelist button",
        trigger: ".control-button.o_pricelist_button",
    }, {
        content: "select fixed pricelist",
        trigger: ".selection-item:contains('min_quantity ordering')",
    }, {
        content: "close the Point of Sale frontend",
        trigger: ".header-button",
    }, {
        content: "confirm closing the frontend",
        trigger: ".header-button",
        run: function() {}, //it's a check,
    }]);

    Tour.register('pos_pricelist', { test: true, url: '/pos/ui' }, steps);
});

odoo.define('point_of_sale.tour.acceptance', function (require) {
    "use strict";

    var Tour = require("web_tour.tour");

    function add_product_to_order(product_name) {
        return [{
            content: 'buy ' + product_name,
            trigger: '.product-list .product-name:contains("' + product_name + '")',
        }, {
            content: 'the ' + product_name + ' have been added to the order',
            trigger: '.order .product-name:contains("' + product_name + '")',
            run: function () {},
        }];
    }

    function set_fiscal_position_on_order(fp_name) {
        return [{
            content: 'set fiscal position',
            trigger: '.control-button.o_fiscal_position_button',
        }, {
            content: 'choose fiscal position ' + fp_name + ' to add to the order',
            trigger: '.popups .popup .selection .selection-item:contains("' + fp_name + '")',
        }, {
            content: 'the fiscal position ' + fp_name + ' has been set to the order',
            trigger: '.control-button.o_fiscal_position_button:contains("' + fp_name + '")',
            run: function () {},
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

    function press_payment_numpad(val) {
        return [{
            content: `press ${val} on payment screen numpad`,
            trigger: `.payment-numpad .input-button:contains("${val}"):visible`,
        }]
    }

    function press_product_numpad(val) {
        return [{
            content: `press ${val} on product screen numpad`,
            trigger: `.numpad .input-button:contains("${val}"):visible`,
        }]
    }

    function selected_payment_has(name, val) {
        return [{
            content: `selected payment is ${name} and has ${val}`,
            trigger: `.paymentlines .paymentline.selected .payment-name:contains("${name}")`,
            extra_trigger: `.paymentlines .paymentline.selected .payment-name:contains("${name}") ~ .payment-amount:contains("${val}")`,
            run: function () {},
        }]
    }

    function selected_orderline_has({ product, price = null, quantity = null }) {
        const result = [];
        if (price !== null) {
            result.push({
                content: `Selected line has product '${product}' and price '${price}'`,
                trigger: `.order-container .orderlines .orderline.selected .product-name:contains("${product}") ~ span.price:contains("${price}")`,
                run: function () {},
            });
        }
        if (quantity !== null) {
            result.push({
                content: `Selected line has product '${product}' and quantity '${quantity}'`,
                trigger: `.order-container .orderlines .orderline.selected .product-name:contains('${product}') ~ .info-list .info em:contains('${quantity}')`,
                run: function () {},
            });
        }
        return result;
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
            trigger: '.payment-screen .button.next.highlight:visible',
        }, {
            content: "verify that the order has been successfully sent to the backend",
            trigger: ".js_connected:visible",
            run: function () {},
        }, {
            content: "click Next Order",
            trigger: '.receipt-screen .button.next.highlight:visible',
        }, {
            content: "check if we left the receipt screen",
            trigger: '.pos-content .screen:not(:has(.receipt-screen))',
            run: function () {},
        }];
    }

    var steps = [{
            content: 'waiting for loading to finish',
            trigger: 'body:not(:has(.loader))',
            run: function () {},
        }, { // Leave category displayed by default
            content: "click category switch",
            trigger: ".breadcrumb-home",
        }];

    steps = steps.concat(add_product_to_order('Desk Organizer'));
    steps = steps.concat(verify_order_total('5.10'));

    steps = steps.concat(add_product_to_order('Desk Organizer'));
    steps = steps.concat(verify_order_total('10.20'));
    steps = steps.concat(goto_payment_screen_and_select_payment_method());

    /*  add payment line of only 5.20
        status:
            order-total := 10.20
            total-payment := 11.70
        expect:
            remaining := 0.00
            change := 1.50
    */
    steps = steps.concat(press_payment_numpad('5'));
    steps = steps.concat(selected_payment_has('Cash', '5.0'));
    steps = steps.concat([{
        content: "verify remaining",
        trigger: '.payment-status-remaining .amount:contains("5.20")',
        run: function () {},
    }, {
        content: "verify change",
        trigger: '.payment-status-change .amount:contains("0.00")',
        run: function () {},
    }]);

    /*  make additional payment line of 6.50
        status:
            order-total := 10.20
            total-payment := 11.70
        expect:
            remaining := 0.00
            change := 1.50
    */
    steps = steps.concat([{
        content: "pay with cash",
        trigger: '.paymentmethod:contains("Cash")',
    }]);
    steps = steps.concat(selected_payment_has('Cash', '5.2'));
    steps = steps.concat(press_payment_numpad('6'))
    steps = steps.concat(selected_payment_has('Cash', '6.0'));
    steps = steps.concat([{
        content: "verify remaining",
        trigger: '.payment-status-remaining .amount:contains("0.00")',
        run: function () {},
    }, {
        content: "verify change",
        trigger: '.payment-status-change .amount:contains("0.80")',
        run: function () {},
    }]);

    steps = steps.concat(finish_order());

    // test opw-672118 orderline subtotal rounding
    steps = steps.concat(add_product_to_order('Desk Organizer'));
    steps = steps.concat(selected_orderline_has({product: 'Desk Organizer', quantity: '1.0'}));
    steps = steps.concat(press_product_numpad('.'))
    steps = steps.concat(selected_orderline_has({product: 'Desk Organizer', quantity: '0.0', price: '0.0'}));
    steps = steps.concat(press_product_numpad('9'))
    steps = steps.concat(selected_orderline_has({product: 'Desk Organizer', quantity: '0.9', price: '4.59'}));
    steps = steps.concat(press_product_numpad('9'))
    steps = steps.concat(selected_orderline_has({product: 'Desk Organizer', quantity: '0.99', price: '5.05'}));
    steps = steps.concat(goto_payment_screen_and_select_payment_method());
    steps = steps.concat(selected_payment_has('Cash', '5.05'));
    steps = steps.concat(finish_order());

    // Test fiscal position one2many map (align with backend)
    steps = steps.concat(add_product_to_order('Letter Tray'));
    steps = steps.concat(selected_orderline_has({product: 'Letter Tray', quantity: '1.0'}));
    steps = steps.concat(verify_order_total('5.28'));
    steps = steps.concat(set_fiscal_position_on_order('FP-POS-2M'));
    steps = steps.concat(verify_order_total('5.52'));

    steps = steps.concat([{
        content: "open closing the Point of Sale frontend popup",
        trigger: ".header-button",
    }, {
        content: "close the Point of Sale frontend",
        trigger: ".close-pos-popup .button:contains('Continue Selling')",
        run: function() {}, //it's a check,
    }]);

    Tour.register('pos_basic_order', { test: true, url: '/pos/ui' }, steps);

});
