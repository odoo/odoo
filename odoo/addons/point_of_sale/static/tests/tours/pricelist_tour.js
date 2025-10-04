/** @odoo-module */
/* global posmodel */

import { registry } from "@web/core/registry";
import * as ProductScreen from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import { roundDecimals as round_di } from "@web/core/utils/numbers";
import { nbsp } from "@web/core/utils/strings";
import * as Numpad from "@point_of_sale/../tests/tours/helpers/NumpadTourMethods";
import * as Order from "@point_of_sale/../tests/tours/helpers/generic_components/OrderWidgetMethods";

function assert(condition, message) {
    if (!condition) {
        throw message || "Assertion failed";
    }
}

function assertProductPrice(product, pricelist_name, quantity, expected_price) {
    return function () {
        var pricelist = posmodel.pricelists.find((pricelist) => pricelist.name === pricelist_name);
        var frontend_price = product.get_price(pricelist, quantity);
        frontend_price = round_di(frontend_price, posmodel.dp["Product Price"]);

        var diff = Math.abs(expected_price - frontend_price);

        assert(
            diff < 0.001,
            JSON.stringify({
                product: product.id,
                product_display_name: product.display_name,
                pricelist_name: pricelist_name,
                quantity: quantity,
            }) +
                " DOESN'T MATCH -> " +
                expected_price +
                " != " +
                frontend_price
        );

        return Promise.resolve();
    };
}

// The global posmodel is only present when the posmodel is instanciated
// So, wait for everythiong to be loaded
var steps = [
    {
        // Leave category displayed by default
        content: "waiting for loading to finish",
        extra_trigger: "body .pos:not(:has(.loader))", // Pos has finished loading
        trigger: "body:not(:has(.o_loading_indicator))", // WebClient has finished Loading
        run: function () {
            var product_wall_shelf = posmodel.db.search_product_in_category(
                0,
                "Wall Shelf Unit"
            )[0];
            var product_small_shelf = posmodel.db.search_product_in_category(0, "Small Shelf")[0];
            var product_magnetic_board = posmodel.db.search_product_in_category(
                0,
                "Magnetic Board"
            )[0];
            var product_monitor_stand = posmodel.db.search_product_in_category(
                0,
                "Monitor Stand"
            )[0];
            var product_desk_pad = posmodel.db.search_product_in_category(0, "Desk Pad")[0];
            var product_letter_tray = posmodel.db.search_product_in_category(0, "Letter Tray")[0];
            var product_whiteboard = posmodel.db.search_product_in_category(0, "Whiteboard")[0];

            assertProductPrice(product_letter_tray, "Public Pricelist", 0, 4.8)()
                .then(assertProductPrice(product_letter_tray, "Public Pricelist", 1, 4.8))
                .then(assertProductPrice(product_letter_tray, "Fixed", 1, 1))
                .then(assertProductPrice(product_wall_shelf, "Fixed", 1, 2))
                .then(assertProductPrice(product_small_shelf, "Fixed", 1, 13.95))
                .then(assertProductPrice(product_wall_shelf, "Percentage", 1, 0))
                .then(assertProductPrice(product_small_shelf, "Percentage", 1, 0.03))
                .then(assertProductPrice(product_magnetic_board, "Percentage", 1, 1.98))
                .then(assertProductPrice(product_wall_shelf, "Formula", 1, 6.86))
                .then(assertProductPrice(product_small_shelf, "Formula", 1, 2.99))
                .then(assertProductPrice(product_magnetic_board, "Formula", 1, 11.98))
                .then(assertProductPrice(product_monitor_stand, "Formula", 1, 8.19))
                .then(assertProductPrice(product_desk_pad, "Formula", 1, 6.98))
                .then(assertProductPrice(product_wall_shelf, "min_quantity ordering", 1, 2))
                .then(assertProductPrice(product_wall_shelf, "min_quantity ordering", 2, 1))
                .then(assertProductPrice(product_letter_tray, "Category vs no category", 1, 2))
                .then(assertProductPrice(product_letter_tray, "Category", 1, 2))
                .then(assertProductPrice(product_wall_shelf, "Product template", 1, 1))
                .then(assertProductPrice(product_wall_shelf, "Dates", 1, 2))
                .then(assertProductPrice(product_small_shelf, "Pricelist base rounding", 1, 13.95))
                .then(assertProductPrice(product_whiteboard, "Public Pricelist", 1, 3.2))
                .then(function () {
                    $(".pos").addClass("done-testing");
                });
        },
    },
    {
        trigger: '.opening-cash-control .button:contains("Open session")',
    },
];

steps = steps.concat([
    {
        content: "wait for unit tests to finish",
        trigger: ".pos.done-testing",
        run: function () {}, // it's a check
    },
    ...ProductScreen.clickHomeCategory(),
    {
        content: "click review button",
        trigger: ".btn-switchpane.review-button",
        mobile: true,
    },
    {
        content: "click more button",
        trigger: ".mobile-more-button",
        mobile: true,
    },
    {
        content: "click pricelist button",
        trigger: ".control-button.o_pricelist_button",
    },
    {
        content: "verify default pricelist is set",
        trigger: ".selection-item.selected:contains('Public Pricelist')",
        run: function () {}, // it's a check
    },
    {
        content: "select fixed pricelist",
        trigger: ".selection-item:contains('Fixed')",
    },
    {
        content: "open partner list",
        trigger: "button.set-partner",
    },
    {
        content: "select Deco Addict",
        trigger: ".partner-line:contains('Deco Addict')",
    },
    {
        content: "click more button",
        trigger: ".mobile-more-button",
        mobile: true,
    },
    {
        content: "click pricelist button",
        trigger: ".control-button.o_pricelist_button",
    },
    {
        content: "verify pricelist changed",
        trigger: ".selection-item.selected:contains('Public Pricelist')",
        run: function () {}, // it's a check
    },
    {
        content: "cancel pricelist dialog",
        trigger: ".button.cancel:visible",
    },
    {
        content: "open customer list",
        trigger: "button.set-partner",
    },
    {
        content: "select Lumber Inc",
        trigger: ".partner-line:contains('Lumber Inc')",
    },
    {
        content: "click more button",
        trigger: ".mobile-more-button",
        mobile: true,
    },
    {
        content: "click pricelist button",
        trigger: ".control-button.o_pricelist_button",
    },
    {
        content: "verify pricelist remained public pricelist ('Not loaded' is not available)",
        trigger: ".selection-item.selected:contains('Public Pricelist')",
        run: function () {}, // it's a check
    },
    {
        content: "cancel pricelist dialog",
        trigger: ".button.cancel:visible",
    },
    {
        content: "go back to the products",
        trigger: ".floor-button",
        mobile: true,
    },
    {
        content: "order 1 kg shelf",
        trigger: ".product:contains('Wall Shelf')",
    },
    {
        content: "click review button",
        trigger: ".btn-switchpane.review-button",
        mobile: true,
    },
    ...Order.hasLine({ productName: "Wall Shelf", quantity: "1.0", withClass: ".selected" }),
    {
        content: "click more button",
        trigger: ".mobile-more-button",
        mobile: true,
    },
    {
        content: "click pricelist button",
        trigger: ".control-button.o_pricelist_button",
    },
    {
        content: "select fixed pricelist",
        trigger: ".selection-item:contains('min_quantity ordering')",
    },
    Numpad.click("2"),
    ...Order.hasLine({ productName: "Wall Shelf", quantity: "2.0", withClass: ".selected" }),
    // verify that unit price of shelf changed to $1
    Order.hasTotal(`$${nbsp}2.00`),
    {
        content: "go back to the products",
        trigger: ".floor-button",
        mobile: true,
    },
    {
        content: "order different shelf",
        trigger: ".product:contains('Small Shelf')",
    },
    {
        content: "click review button",
        trigger: ".btn-switchpane.review-button",
        mobile: true,
    },
    ...Order.hasLine({ productName: "Small Shelf", quantity: "1.0", withClass: ".selected" }),
    Numpad.click("Price"),
    Numpad.isActive("Price"),
    Numpad.click("5"),
    ...Order.hasLine({ productName: "Small Shelf", price: "5.0", withClass: ".selected" }),
    Numpad.click("Qty"),
    Numpad.isActive("Qty"),
    {
        content: "click more button",
        trigger: ".mobile-more-button",
        mobile: true,
    },
    {
        content: "click pricelist button",
        trigger: ".control-button.o_pricelist_button",
    },
    {
        content: "select public pricelist",
        trigger: ".selection-item:contains('Public Pricelist')",
    },
    // verify that the boni shelf have been recomputed and the shelf have not (their price was manually overridden)
    Order.hasTotal(`$${nbsp}8.96`),
    {
        content: "click more button",
        trigger: ".mobile-more-button",
        mobile: true,
    },
    {
        content: "click pricelist button",
        trigger: ".control-button.o_pricelist_button",
    },
    {
        content: "select fixed pricelist",
        trigger: ".selection-item:contains('min_quantity ordering')",
    },
    {
        content: "open the navbar menu",
        trigger: ".menu-button",
    },
    {
        content: "confirm closing the frontend",
        trigger: ".close-button",
        run: function () {}, //it's a check,
    },
]);

registry.category("web_tour.tours").add("pos_pricelist", {
    test: true,
    url: "/pos/ui",
    steps: () => steps,
});
