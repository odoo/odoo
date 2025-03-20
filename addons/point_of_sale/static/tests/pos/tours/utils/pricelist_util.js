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
                const product1 = posmodel.data.models["product.template"].find(
                    (p) => p.display_name === "Product for pricelist 1"
                );
                const product2 = posmodel.data.models["product.template"].find(
                    (p) => p.display_name === "Product for pricelist 2"
                );
                const product3 = posmodel.data.models["product.template"].find(
                    (p) => p.display_name === "Product for pricelist 3"
                );
                const product4 = posmodel.data.models["product.template"].find(
                    (p) => p.display_name === "Product for pricelist 4"
                );
                const product5 = posmodel.data.models["product.template"].find(
                    (p) => p.display_name === "Product for pricelist 5"
                );
                const product6 = posmodel.data.models["product.template"].find(
                    (p) => p.display_name === "Product for pricelist 6"
                );

                assertProductPrice(product6, "Public Pricelist", 0, 4.8)()
                    .then(assertProductPrice(product6, "Public Pricelist", 1, 4.8))
                    .then(assertProductPrice(product6, "Fixed", 1, 1))
                    .then(assertProductPrice(product1, "Fixed", 1, 2))
                    .then(assertProductPrice(product2, "Fixed", 1, 13.95))
                    .then(assertProductPrice(product1, "Percentage", 1, 0))
                    .then(assertProductPrice(product2, "Percentage", 1, 0.03))
                    .then(assertProductPrice(product3, "Percentage", 1, 1.98))
                    .then(assertProductPrice(product1, "Formula", 1, 6.86))
                    .then(assertProductPrice(product2, "Formula", 1, 2.99))
                    .then(assertProductPrice(product3, "Formula", 1, 11.98))
                    .then(assertProductPrice(product4, "Formula", 1, 8.19))
                    .then(assertProductPrice(product5, "Formula", 1, 6.98))
                    .then(assertProductPrice(product1, "min_quantity ordering", 1, 2))
                    .then(assertProductPrice(product1, "min_quantity ordering", 2, 1))
                    .then(assertProductPrice(product6, "Category vs no category", 1, 2))
                    .then(assertProductPrice(product6, "Category", 1, 2))
                    .then(assertProductPrice(product1, "Product template", 1, 1))
                    .then(assertProductPrice(product1, "Dates", 1, 2))
                    .then(assertProductPrice(product2, "Pricelist base rounding", 1, 13.95))
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
