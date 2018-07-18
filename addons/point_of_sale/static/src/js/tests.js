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
                    return (new $.Deferred()).resolve();
                });
        };
    }

    var steps = [{
        content: 'waiting for loading to finish',
        trigger: '.o_main_content:has(.loader:hidden)',
        run: function () {
            var product_wall_shelf = posmodel.db.search_product_in_category(0, 'Wall Shelf Unit')[0];
            var product_small_shelf = posmodel.db.search_product_in_category(0, 'Small Shelf')[0];
            var product_magnetic_board = posmodel.db.search_product_in_category(0, 'Magnetic Board')[0];
            var product_monitor_stand = posmodel.db.search_product_in_category(0, 'Monitor Stand')[0];
            var product_desk_pad = posmodel.db.search_product_in_category(0, 'Desk Pad')[0];
            var product_letter_tray = posmodel.db.search_product_in_category(0, 'Letter Tray')[0];
            var product_whiteboard = posmodel.db.search_product_in_category(0, 'Whiteboard')[0];
            var product_miscellaneous = posmodel.db.search_product_in_category(0, 'Miscellaneous')[0];

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
                .then(compare_backend_frontend(product_miscellaneous, 'Cost base', 1, undefined))
                .then(compare_backend_frontend(product_miscellaneous, 'Pricelist base', 1, undefined))
                .then(compare_backend_frontend(product_miscellaneous, 'Pricelist base 2', 1, undefined))
                .then(compare_backend_frontend(product_small_shelf, 'Pricelist base rounding', 1, undefined))
                .then(compare_backend_frontend(product_whiteboard, 'Public Pricelist', 1, undefined))
                .then(function () {
                    $('.pos').addClass('done-testing');
                });
        },
    }];

    steps = steps.concat([{
        content: "wait for unit tests to finish",
        trigger: ".pos.done-testing",
        run: function () {}, // it's a check
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
        content: "prices should be updated in the product screen",
        trigger: ".product:contains('Miscellaneous'):contains('$ 1.00')",
        run: function () {}, // it's a check
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
        content: "prices should be updated in the product screen",
        trigger: ".product:contains('Miscellaneous'):contains('$ 18.00')",
        run: function () {}, // it's a check
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
        content: "verify that unit price of shelf changed to $1",
        trigger: ".total > .value:contains('$ 2.00')",
    }, {
        content: "order different shelf",
        trigger: ".product:contains('Small Shelf')",
    }, {
        content: "change to price mode",
        trigger: ".numpad button:contains('Price')",
    }, {
        content: "manually override the unit price of these shelf to $5",
        trigger: ".numpad button.input-button:visible:contains('5')",
    }, {
        content: "change back to qty mode",
        trigger: ".numpad button:contains('Qty')",
    }, {
        content: "click pricelist button",
        trigger: ".control-button.o_pricelist_button",
    }, {
        content: "select public pricelist",
        trigger: ".selection-item:contains('Public Pricelist')",
    }, {
        content: "verify that the boni shelf have been recomputed and the\
shelf have not (their price was manually overriden)",
        trigger: ".total > .value:contains('$ 8.96')",
    }, {
        content: "click pricelist button",
        trigger: ".control-button.o_pricelist_button",
    }, {
        content: "select fixed pricelist",
        trigger: ".selection-item:contains('min_quantity ordering')",
    }, {
        content: "order 1 miscellaneous product",
        trigger: ".product:contains('Miscellaneous')",
    }, {
        content: "order 1 miscellaneous product",
        trigger: ".product:contains('Miscellaneous')",
    }, {
        content: "order 1 miscellaneous product",
        trigger: ".product:contains('Miscellaneous')",
    }, {
        content: "verify there is one line with 3 miscellaneous products",
        trigger: ".orderline:contains('Miscellaneous') em:contains('3.000')",
        run: function () {}, // it's a check
    }, {
        content: "close the Point of Sale frontend",
        trigger: ".header-button",
    }, {
        content: "confirm closing the frontend",
        trigger: ".header-button",
    }]);

    Tour.register('pos_pricelist', { test: true, url: '/pos/web' }, steps);
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

    steps = steps.concat(add_product_to_order('Desk Organizer'));
    steps = steps.concat(verify_order_total('5.10'));

    steps = steps.concat(add_product_to_order('Desk Organizer'));
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
    steps = steps.concat(add_product_to_order('Desk Organizer'));
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

    Tour.register('pos_basic_order', { test: true, url: '/pos/web' }, steps);

});
