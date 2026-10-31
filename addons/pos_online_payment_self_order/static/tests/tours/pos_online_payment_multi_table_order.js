import * as ChromePos from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as ChromeRestaurant from "@pos_restaurant/../tests/tours/utils/chrome";
import * as ProductScreenPos from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as ProductScreenResto from "@pos_restaurant/../tests/tours/utils/product_screen_util";
import * as TicketScreen from "@point_of_sale/../tests/pos/tours/utils/ticket_screen_util";
import { registry } from "@web/core/registry";

const Chrome = { ...ChromePos, ...ChromeRestaurant };
const ProductScreen = { ...ProductScreenPos, ...ProductScreenResto };

registry.category("web_tour.tours").add("test_online_payment_self_multi_company_payment", {
    steps: () => [
        {
            trigger: 'button[name="o_payment_submit_button"]:not(:disabled)',
        },
    ],
});

registry.category("web_tour.tours").add("test_online_payment_pos_self_order_preparation_changes", {
    steps: () =>
        [
            Chrome.startPoS(),
            Chrome.clickOrders(),
            Chrome.orderTrackerShown(),
            TicketScreen.checkStatus("Self-order", "Ongoing"),
            TicketScreen.selectOrder("Self-order"),
            ProductScreen.clickReview(),
            ProductScreen.orderlineIsToOrder("Fanta"),
        ].flat(),
});
