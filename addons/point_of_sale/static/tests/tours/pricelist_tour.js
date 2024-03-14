/** @odoo-module */
/* global posmodel */

import { registry } from "@web/core/registry";
import * as ProductScreen from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import { roundDecimals as round_di } from "@web/core/utils/numbers";
import { nbsp } from "@web/core/utils/strings";
import * as Numpad from "@point_of_sale/../tests/tours/helpers/NumpadTourMethods";
import * as Order from "@point_of_sale/../tests/tours/helpers/generic_components/OrderWidgetMethods";
import * as Dialog from "@point_of_sale/../tests/tours/helpers/DialogTourMethods";

function assert(condition, message) {
    if (!condition) {
        throw message || "Assertion failed";
    }
}

function assertProductPrice(product, pricelist_name, quantity, expected_price) {
    return function () {
        var pricelist = posmodel.data.models["product.pricelist"].find(
            (pricelist) => pricelist.name === pricelist_name
        );
        var frontend_price = product.get_price(pricelist, quantity);
        const dp = posmodel.data.models["decimal.precision"].find(
            (dp) => dp.name === "Product Price"
        );
        frontend_price = round_di(frontend_price, dp.digits);
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

registry.category("web_tour.tours").add("pos_pricelist", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            // The global posmodel is only present when the posmodel is instantiated
            // So, wait for everything to be loaded
            {
                content: "waiting for loading to finish",
                trigger: "body:not(:has(.pos-loader))", // Pos has finished loading
                in_modal: false,
                run: function () {
                    var product_wall_shelf = posmodel.data.models["product.product"]
                        .getAll()
                        .find((p) => p.display_name === "Wall Shelf Unit");
                    var product_small_shelf = posmodel.data.models["product.product"]
                        .getAll()
                        .find((p) => p.display_name === "Small Shelf");
                    var product_magnetic_board = posmodel.data.models["product.product"]
                        .getAll()
                        .find((p) => p.display_name === "Magnetic Board");
                    var product_monitor_stand = posmodel.data.models["product.product"]
                        .getAll()
                        .find((p) => p.display_name === "Monitor Stand");
                    var product_desk_pad = posmodel.data.models["product.product"]
                        .getAll()
                        .find((p) => p.display_name === "Desk Pad");
                    var product_letter_tray = posmodel.data.models["product.product"]
                        .getAll()
                        .find((p) => p.display_name === "Letter Tray");

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
                        .then(
                            assertProductPrice(product_letter_tray, "Category vs no category", 1, 2)
                        )
                        .then(assertProductPrice(product_letter_tray, "Category", 1, 2))
                        .then(assertProductPrice(product_wall_shelf, "Product template", 1, 1))
                        .then(assertProductPrice(product_wall_shelf, "Dates", 1, 2))
                        .then(
                            assertProductPrice(
                                product_small_shelf,
                                "Pricelist base rounding",
                                1,
                                13.95
                            )
                        )
                        .then(function () {
                            $(".pos").addClass("done-testing");
                        });
                },
            },
            {
                content: "wait for unit tests to finish",
                trigger: ".pos.done-testing",
                in_modal: false,
                run: function () {}, // it's a check
            },
            Dialog.confirm("Open session"),
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
                trigger: ".control-buttons button.o_pricelist_button",
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
                trigger: ".control-buttons button.o_pricelist_button",
            },
            {
                content: "verify pricelist changed",
                trigger: ".selection-item.selected:contains('Public Pricelist')",
                run: function () {}, // it's a check
            },
            Dialog.cancel(),
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
                trigger: ".control-buttons button.o_pricelist_button",
            },
            {
                content:
                    "verify pricelist remained public pricelist ('Not loaded' is not available)",
                trigger: ".selection-item.selected:contains('Public Pricelist')",
                run: function () {}, // it's a check
            },
            Dialog.cancel(),
            ProductScreen.goBackToMainScreen(),
            {
                content: "show all the products",
                trigger: ".show-products-mobile",
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
            ...Order.hasLine({
                productName: "Wall Shelf",
                quantity: "1.0",
                withClass: ".selected",
            }),
            {
                content: "click more button",
                trigger: ".mobile-more-button",
                mobile: true,
            },
            {
                content: "click pricelist button",
                trigger: ".control-buttons button.o_pricelist_button",
            },
            {
                content: "select fixed pricelist",
                trigger: ".selection-item:contains('min_quantity ordering')",
            },
            Numpad.click("2"),
            ...Order.hasLine({
                productName: "Wall Shelf",
                quantity: "2.0",
                withClass: ".selected",
            }),
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
            ...Order.hasLine({
                productName: "Small Shelf",
                quantity: "1.0",
                withClass: ".selected",
            }),
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
                trigger: ".control-buttons button.o_pricelist_button",
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
                trigger: ".control-buttons button.o_pricelist_button",
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
        ].flat(),
});
