/* global posmodel */

import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import { registry } from "@web/core/registry";
import { inLeftSide } from "@point_of_sale/../tests/pos/tours/utils/common";
import * as Numpad from "@point_of_sale/../tests/generic_helpers/numpad_util";

registry.category("web_tour.tours").add("test_baseline_between_frontend_and_backend", {
    steps: () =>
        [
            Chrome.startPoS(),
            ProductScreen.clickDisplayedProduct("Test Product 1"),
            ProductScreen.clickDisplayedProduct("Test Product 2"),
            inLeftSide([
                ...["+/-"].map(Numpad.click),
                ...ProductScreen.selectedOrderlineHasDirect("Test Product 2", "-1.0"),
            ]),
            ProductScreen.totalAmountIs("7,771.00"),
            {
                trigger: "body",
                content: "Create an order with a product with dynamic price",
                run: async () => {
                    const data = JSON.stringify(posmodel.getOrder()._computeAllPrices());
                    const result = await posmodel.syncAllOrders({ orders: [posmodel.getOrder()] });
                    const orderId = result[0].id;
                    await posmodel.data.call("pos.order", "get_frontend_data", [[orderId], data]);
                },
            },
        ].flat(),
});
