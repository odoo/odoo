import { registry } from "@web/core/registry";
import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import * as CustomerDisplay from "@point_of_sale/../tests/customer_display/customer_display_utils";

const ADD_PRODUCT = JSON.stringify({
    ...JSON.parse(CustomerDisplay.ADD_PRODUCT),
    loyaltyData: [
        {
            couponId: 101,
            points: {
                won: 25,
                spent: 10,
                total: 65,
                balance: 50,
                name: "Loyalty Points",
            },
        },
    ],
});

registry.category("web_tour.tours").add("test_customer_display_loyalty_points", {
    steps: () =>
        [
            CustomerDisplay.addProduct(ADD_PRODUCT, "add product"),
            Order.hasLine({ productName: "Letter Tray", price: "2,972.75" }),
            CustomerDisplay.amountIs("Total", "2,972.75"),
            {
                content: "Check that the title should be Loyalty Points",
                trigger: ".loyalty-points-title:contains(Loyalty Points)",
            },
            {
                content: "Check loyalty balance points are displayed correctly",
                trigger: ".loyalty-points-balance:contains(50)",
            },
            {
                content: "Check loyalty won points are displayed correctly in green",
                trigger: ".loyalty-points-won.text-success:contains(+ 25)",
            },
            {
                content: "Check loyalty spent points are displayed correctly in red",
                trigger: ".loyalty-points-spent.text-danger:contains(- 10)",
            },
            {
                content: "Check loyalty total points are displayed correctly",
                trigger: ".loyalty-points-total.fw-bolder:contains(65)",
            },
        ].flat(),
});
