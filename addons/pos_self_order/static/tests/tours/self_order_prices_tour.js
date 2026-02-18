/* global posmodel */

import { registry } from "@web/core/registry";
import * as Utils from "@pos_self_order/../tests/tours/utils/common";
import * as ProductPage from "@pos_self_order/../tests/tours/utils/product_page_util";
import * as ConfirmationPage from "@pos_self_order/../tests/tours/utils/confirmation_page_util";
import * as LandingPage from "@pos_self_order/../tests/tours/utils/landing_page_util";

const comparePricesWithBackend = {
    trigger: "body",
    run: async () => {
        const order = posmodel.currentOrder;
        const orderTotal = order.displayPrice;
        const allUnitPrices = order.lines.map((l) => l.price_unit);
        await posmodel.sendDraftOrderToServer();
        const orderTotalAfterSync = order.displayPrice;
        const allUnitPricesAfterSync = order.lines.map((l) => l.price_unit);

        if (orderTotal !== orderTotalAfterSync) {
            throw new Error(
                `The total price changed after sync: before=${orderTotal}, after=${orderTotalAfterSync}`
            );
        }

        for (let i = 0; i < allUnitPrices.length; i++) {
            if (allUnitPrices[i] !== allUnitPricesAfterSync[i]) {
                throw new Error(
                    `The unit price of line ${i} changed after sync: before=${allUnitPrices[i]}, after=${allUnitPricesAfterSync[i]}`
                );
            }
        }
    },
};

const forceCancel = {
    trigger: "body",
    run: () => {
        posmodel.currentOrder.delete();
    },
};

const commonSteps = [
    Utils.clickBtn("Add to Cart"),
    ProductPage.clickProduct("Random Product 1"),
    ProductPage.clickProduct("Random Product 2"),
    ProductPage.clickProduct("Random Product 3"),
    Utils.clickBtn("Checkout"),
    comparePricesWithBackend,
    Utils.clickBtn("Order"),
    ConfirmationPage.orderNumberShown(),
    Utils.clickBtn("Ok"),
    Utils.checkBtn("My Order"),
    forceCancel,
];

registry.category("web_tour.tours").add("test_combo_prices", {
    steps: () => [
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Big Combo"),
        ...ProductPage.setupCombo([
            { product: "Green 1", attributes: [] },
            { product: "Green 2", attributes: [] },
        ]),
        ...ProductPage.setupCombo([
            { product: "Red 1", attributes: [] },
            { product: "Red 2", attributes: [] },
        ]),
        ...ProductPage.setupCombo([
            { product: "Purple 1", attributes: [] },
            { product: "Purple 2", attributes: [] },
        ]),
        ...commonSteps,
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Big Combo"),
        ...ProductPage.setupCombo([
            { product: "Green 1", attributes: [] },
            { product: "Green 2", attributes: [] },
        ]),
        ...ProductPage.setupCombo([
            { product: "Red 1", attributes: [] },
            { product: "Red 1", attributes: [] },
            { product: "Red 2", attributes: [] },
            { product: "Red 2", attributes: [] },
            { product: "Red 2", attributes: [] },
        ]),
        ...ProductPage.setupCombo([
            { product: "Purple 1", attributes: [] },
            { product: "Purple 1", attributes: [] },
            { product: "Purple 2", attributes: [] },
            { product: "Purple 2", attributes: [] },
            { product: "Purple 2", attributes: [] },
            { product: "Purple 2", attributes: [] },
            { product: "Purple 2", attributes: [] },
            { product: "Purple 2", attributes: [] },
            { product: "Purple 2", attributes: [] },
            { product: "Purple 2", attributes: [] },
        ]),
        ...commonSteps,
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Big Combo"),
        ...ProductPage.setupCombo([
            { product: "Green 1", attributes: [] },
            {
                product: "Green 3",
                attributes: [
                    { name: "Size", value: "Big" },
                    { name: "Color", value: "Blue" },
                ],
            },
        ]),
        ...ProductPage.setupCombo([
            { product: "Red 1", attributes: [] },
            { product: "Red 1", attributes: [] },
            {
                product: "Red 3",
                attributes: [
                    { name: "Size", value: "Big" },
                    { name: "Color", value: "Blue" },
                ],
            },
            { product: "Red 3", attributes: [] },
            { product: "Red 3", attributes: [] },
        ]),
        ...ProductPage.setupCombo([
            { product: "Purple 1", attributes: [] },
            { product: "Purple 1", attributes: [] },
            { product: "Purple 2", attributes: [] },
            { product: "Purple 2", attributes: [] },
            { product: "Purple 2", attributes: [] },
            { product: "Purple 2", attributes: [] },
            { product: "Purple 2", attributes: [] },
            { product: "Purple 2", attributes: [] },
            {
                product: "Purple 3",
                attributes: [
                    { name: "Size", value: "Small" },
                    { name: "Color", value: "Red" },
                ],
            },
            { product: "Purple 3", attributes: [] },
        ]),
        ...commonSteps,
    ],
});

registry.category("web_tour.tours").add("test_price_between_frontend_and_backend", {
    steps: () => [
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Product with attributes"),
        ...ProductPage.setupAttribute([
            { name: "Price Extra", value: "Big" },
            { name: "No Price Extra", value: "Two" },
        ]),
        ProductPage.clickProduct("Product with attributes"),
        ...ProductPage.setupAttribute([
            { name: "Price Extra", value: "Big" },
            { name: "No Price Extra", value: "Two" },
        ]),
        ProductPage.clickProduct("Product with attributes"),
        ...ProductPage.setupAttribute([
            { name: "Price Extra", value: "Big" },
            { name: "No Price Extra", value: "One" },
        ]),
        ProductPage.clickProduct("Product with attributes"),
        ...ProductPage.setupAttribute([
            { name: "Price Extra", value: "Small" },
            { name: "No Price Extra", value: "Two" },
        ]),
        ProductPage.clickProduct("Product with attributes"),
        ...ProductPage.setupAttribute([
            { name: "Price Extra", value: "Small" },
            { name: "No Price Extra", value: "Two" },
        ]),
        comparePricesWithBackend,
    ],
});

/**
 * This will create one lines with extra price and attributes
 * 257.58 Order total
 * 106.44 Line price unit
 */
const commonStepWithSpecificPrice = [
    ProductPage.clickProduct("Product with attributes"),
    ...ProductPage.setupAttribute([
        { name: "Price Extra", value: "Big" },
        { name: "No Price Extra", value: "Two" },
    ]),
    ProductPage.clickProduct("Product with attributes"),
    ...ProductPage.setupAttribute([
        { name: "Price Extra", value: "Big" },
        { name: "No Price Extra", value: "Two" },
    ]),
];

registry.category("web_tour.tours").add("test_prices_are_immutable_from_frontend", {
    steps: () => [
        Utils.clickBtn("Order Now"),
        ...commonStepWithSpecificPrice,
        {
            trigger: "body",
            run: async () => {
                const order = posmodel.currentOrder;
                const line = order.lines[0];
                line.price_unit = 0;
                line.tax_ids = [];
                const orderTotal = order.displayPrice;
                const allUnitPrices = order.lines.map((l) => l.price_unit);

                if (orderTotal !== 0) {
                    throw new Error(
                        `The total price should be 0 after changing the line price_unit to 0, but it is ${orderTotal}`
                    );
                }

                if (allUnitPrices.some((p) => p !== 0)) {
                    throw new Error(
                        `All line price_unit should be 0 after changing the line price_unit to 0, but they are ${allUnitPrices.join(
                            ", "
                        )}`
                    );
                }

                // 257.58 Order total
                // 106.44 Line price unit
                await posmodel.sendDraftOrderToServer();
                const orderTotalAfterSync = order.displayPrice;
                const allUnitPricesAfterSync = order.lines.map((l) => l.price_unit);

                if (orderTotalAfterSync !== 257.58) {
                    throw new Error(
                        `The total price should be 257.58 after sync, but it is ${orderTotalAfterSync}`
                    );
                }

                if (allUnitPricesAfterSync.some((p) => p !== 106.44)) {
                    throw new Error(
                        `All line price_unit should be 106.44 after sync, but they are ${allUnitPricesAfterSync.join(
                            ", "
                        )}`
                    );
                }
            },
        },
    ],
});

registry.category("web_tour.tours").add("test_pricelist_should_not_be_changed_from_frontend", {
    steps: () => [
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-Takeout"),
        ...commonStepWithSpecificPrice,
        {
            trigger: "body",
            run: async () => {
                const order = posmodel.currentOrder;
                const amountTotal = order.displayPrice;
                const freePricelist = posmodel.models["product.pricelist"].find(
                    (p) => p.name === "Free Pricelist"
                );

                if (order.pricelist_id.name !== "10% Pricelist") {
                    throw new Error(
                        `The pricelist should be "10% Pricelist", but it is ${order.pricelist_id.name}`
                    );
                }

                if (amountTotal !== 231.82) {
                    throw new Error(
                        `The total price should be 231.82 with 10% discount, but it is ${amountTotal}`
                    );
                }

                order.pricelist_id = freePricelist;
                order.lines = [];
            },
        },
        ...commonStepWithSpecificPrice,
        {
            trigger: "body",
            run: async () => {
                const order = posmodel.currentOrder;
                const amountTotal = order.displayPrice;

                if (amountTotal !== 0) {
                    throw new Error(
                        `The total price should be 0 with free pricelist, but it is ${amountTotal}`
                    );
                }

                await posmodel.sendDraftOrderToServer();
                const amountTotalAfterSync = order.displayPrice;
                if (amountTotalAfterSync === 0) {
                    throw new Error(
                        `The total price should be 231.82 after sync, but it is ${amountTotalAfterSync}`
                    );
                }
            },
        },
    ],
});

registry.category("web_tour.tours").add("test_pricelist_price_between_frontend_and_backend", {
    steps: () => [
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-Takeout"),
        ...commonStepWithSpecificPrice,
        comparePricesWithBackend,
    ],
});
