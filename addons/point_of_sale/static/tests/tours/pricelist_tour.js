/** @odoo-module */
/* global posmodel */

import Tour from "web_tour.tour";
import utils from "web.utils";
var round_di = utils.round_decimals;

function assert(condition, message) {
    if (!condition) {
        throw message || "Assertion failed";
    }
}

function assertProductPrice(product, pricelist_name, quantity, expected_price) {
    return function () {
        var pricelist = _.findWhere(posmodel.pricelists, { name: pricelist_name });
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
    {
        content: "click category switch",
        trigger: ".breadcrumb-home",
        run: "click",
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
        content: "click pricelist button",
        trigger: ".control-button.o_pricelist_button",
    },
    {
        content: "select fixed pricelist",
        trigger: ".selection-item:contains('min_quantity ordering')",
    },
    {
        content: "order 1 kg shelf",
        trigger: ".product:contains('Wall Shelf')",
    },
    {
        content: "change qty to 2 kg",
        trigger: ".numpad button.input-button:visible:contains('2')",
    },
    {
        content: "qty of Wall Shelf line should be 2",
        trigger:
            ".order-container .orderlines .orderline.selected .product-name:contains('Wall Shelf')",
        extra_trigger:
            ".order-container .orderlines .orderline.selected .product-name:contains('Wall Shelf') ~ .info-list .info em:contains('2.0')",
        run: function () {},
    },
    {
        content: "verify that unit price of shelf changed to $1",
        trigger: ".total > .value:contains('$ 2.00')",
        run: function () {},
    },
    {
        content: "order different shelf",
        trigger: ".product:contains('Small Shelf')",
    },
    {
        content: "Small Shelf line should be selected with quantity 1",
        trigger:
            ".order-container .orderlines .orderline.selected .product-name:contains('Small Shelf')",
        extra_trigger:
            ".order-container .orderlines .orderline.selected .product-name:contains('Small Shelf') ~ .info-list .info em:contains('1.0')",
        run: function () {},
    },
    {
        content: "change to price mode",
        trigger: ".numpad button:contains('Price')",
    },
    {
        content: "make sure price mode is activated",
        trigger: ".numpad button.selected-mode:contains('Price')",
        run: function () {},
    },
    {
        content: "manually override the unit price of these shelf to $5",
        trigger: ".numpad button.input-button:visible:contains('5')",
    },
    {
        content: "Small Shelf line should be selected with unit price of 5",
        trigger:
            ".order-container .orderlines .orderline.selected .product-name:contains('Small Shelf')",
        extra_trigger:
            ".order-container .orderlines .orderline.selected .product-name:contains('Small Shelf') ~ .price:contains('5.0')",
    },
    {
        content: "change back to qty mode",
        trigger: ".numpad button:contains('Qty')",
    },
    {
        content: "make sure qty mode is activated",
        trigger: ".numpad button.selected-mode:contains('Qty')",
        run: function () {},
    },
    {
        content: "click pricelist button",
        trigger: ".control-button.o_pricelist_button",
    },
    {
        content: "select public pricelist",
        trigger: ".selection-item:contains('Public Pricelist')",
    },
    {
        content:
            "verify that the boni shelf have been recomputed and the shelf have not (their price was manually overridden)",
        trigger: ".total > .value:contains('$ 8.96')",
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
        content: "close the Point of Sale frontend",
        trigger: ".header-button",
    },
    {
        content: "confirm closing the frontend",
        trigger: ".header-button",
        run: function () {}, //it's a check,
    },
]);

Tour.register("pos_pricelist", { test: true, url: "/pos/ui" }, steps);
