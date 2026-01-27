/* global posmodel */

import { registry } from "@web/core/registry";
import * as Utils from "@pos_self_order/../tests/tours/utils/common";
import * as ProductPage from "@pos_self_order/../tests/tours/utils/product_page_util";
import * as ConfirmationPage from "@pos_self_order/../tests/tours/utils/confirmation_page_util";

const checkPricesInCombo = {
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
    checkPricesInCombo,
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
