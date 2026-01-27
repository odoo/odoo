/* global posmodel */

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
        var frontend_price = product.getPrice(
            pricelist,
            quantity,
            0,
            false,
            product.product_variant_ids[0]
        );
        const ProductPrice = posmodel.data.models["decimal.precision"].find(
            (dp) => dp.name === "Product Price"
        );
        frontend_price = ProductPrice.round(frontend_price);
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

export function setUp() {
    return [
        // The global posmodel is only present when the posmodel is instantiated
        // So, wait for everything to be loaded
        {
            content: "waiting for loading to finish",
            trigger: "body:not(:has(.pos-loader))", // Pos has finished loading
            run: function () {
                var product_wall_shelf = posmodel.data.models["product.template"]
                    .getAll()
                    .find((p) => p.display_name === "Wall Shelf Unit");
                var product_small_shelf = posmodel.data.models["product.template"]
                    .getAll()
                    .find((p) => p.display_name === "Small Shelf");
                var product_magnetic_board = posmodel.data.models["product.template"]
                    .getAll()
                    .find((p) => p.display_name === "Magnetic Board");
                var product_monitor_stand = posmodel.data.models["product.template"]
                    .getAll()
                    .find((p) => p.display_name === "Monitor Stand");
                var product_desk_pad = posmodel.data.models["product.template"]
                    .getAll()
                    .find((p) => p.display_name === "Desk Pad");
                var product_letter_tray = posmodel.data.models["product.template"]
                    .getAll()
                    .find((p) => p.display_name === "Letter Tray");

                assertProductPrice(product_letter_tray, "Public Pricelist", 0, 4.8)()
                    .then(assertProductPrice(product_letter_tray, "Public Pricelist", 1, 4.8))
                    .then(assertProductPrice(product_letter_tray, "Fixed", 1, 1))
                    .then(assertProductPrice(product_letter_tray, "Fixed", -1, 1))
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
                    .then(
                        assertProductPrice(product_small_shelf, "Pricelist base rounding", 1, 13.95)
                    )
                    .then(function () {
                        document.querySelector(".pos").classList.add("done-testing");
                    });
            },
        },
    ];
}

export function waitForUnitTest() {
    return [
        {
            content: "wait for unit tests to finish",
            trigger: ".pos.done-testing",
        },
    ];
}
