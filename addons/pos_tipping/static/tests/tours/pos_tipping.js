odoo.define('pos_tipping.tour.acceptance', function (require) {
    "use strict";

    var Tour = require("web_tour.tour");
    var helper = require("point_of_sale.tour_helper");

    function new_order() {
        return [{
            content: 'open new order',
            trigger: '.neworder-button',
        }];
    }

    function search(customer_name) {
        var $search = $(".search-input");
        $search.select();

        // native keydown handlers aren't triggered by fake keydown
        // events, so fill the input with val() and send a dummy
        // keydown event to trigger the widget's js.
        $search.val(customer_name);
        $search.trigger("keydown");

        setTimeout(function () {
            $search.addClass("test-search-done");
        }, 100);
    }

    function search_order(customer_name, interface_button) {
        return [{
            content: "open " + interface_button + " search",
            trigger: interface_button,
        }, {
            content: "search for " + customer_name,
            trigger: ".search-input",
            run: function () {
                search(customer_name);
            }
        }, {
            content: "wait for the search to finish",
            trigger: ".search-input.test-search-done",
            run: function () {
                $(".search-input").removeClass("test-search-done");
            }
        }];
    }

    function select_list_order(customer_name, interface_button) {
        var steps = search_order(customer_name, interface_button);
        steps = steps.concat([{
            content: "only 1 order should be visible",
            trigger: ".list-table-contents > tr",
            run: function () {
                var found_orders = $(".list-table-contents > tr:visible").length;
                if (found_orders !== 1) {
                    console.error("Found " + found_orders + " orders when only 1 order was expected.");
                }
            }
        }, {
            content: "select the " + customer_name + " order",
            trigger: ".list-table-contents > tr",
        }]);

        return steps;
    }

    function select_table(table_name) {
        return [{
            content: "select table " + table_name,
            trigger: '.table:contains("' + table_name + '")'
        }];
    }

    function back_to_floor() {
        return [{
            content: "go back to floor plan",
            trigger: ".floor-button"
        }];
    }

    function tip_customer_order(customer_name, amount) {
        var steps = select_list_order(customer_name, ".tip-orders");
        steps = steps.concat(helper.generate_keypad_steps(amount.toString(), ".popup-number"));
        steps = steps.concat([{
            content: "confirm tip of " + amount + " for " + customer_name,
            trigger: ".popup-number .confirm"
        }]);

        // leave screen to force the tip rpc
        steps = steps.concat([{
            content: "leave tip screen",
            trigger: ".button.back:visible"
        }]);

        // verify tip amount
        steps = steps.concat(select_list_order(customer_name, ".tip-orders"));
        steps = steps.concat({
            content: "verify tip of " + amount + " for " + customer_name,
            trigger: ".tip-amount:visible:contains('1.00')"
        });

        return steps;
    }

    var steps = helper.wait_for_load();

    // test order switcher
    steps = steps.concat(select_table("t1"));
    steps = steps.concat(helper.add_product_to_order("Wall Shelf Unit"));
    steps = steps.concat(helper.set_customer("Deco Addict"));
    steps = steps.concat(new_order());
    steps = steps.concat(helper.set_customer("Lumber Inc"));
    steps = steps.concat(helper.add_product_to_order("Letter Tray"));
    steps = steps.concat(helper.add_product_to_order("Magnetic Board"));
    steps = steps.concat(helper.add_product_to_order("Desk Pad"));

    steps = steps.concat(back_to_floor());
    steps = steps.concat(select_table("t2"));
    steps = steps.concat(helper.set_customer("TEST PARTNER"));
    steps = steps.concat(helper.add_product_to_order("Monitor Stand"));
    
    steps = steps.concat(select_list_order("Deco Addict", ".search-orders"));
    steps = steps.concat(helper.check_product_in_order("Wall Shelf Unit"));
    steps = steps.concat(select_list_order("Lumber Inc", ".search-orders"));
    steps = steps.concat(helper.check_product_in_order("Letter Tray"));
    steps = steps.concat(select_list_order("TEST PARTNER", ".search-orders"));
    steps = steps.concat(helper.check_product_in_order("Monitor Stand"));

    // test tipping
    steps = steps.concat(helper.goto_payment_screen_and_select_payment_method("Bank"));
    steps = steps.concat(helper.finish_order());
    steps = steps.concat(tip_customer_order("TEST PARTNER", 1.00));

    steps = steps.concat(helper.close_pos());

    Tour.register("pos_tipping_acceptance", { test: true, url: "/pos/web" }, steps);
});
