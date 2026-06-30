import * as ChromePos from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as ChromeRestaurant from "@pos_restaurant/../tests/tours/utils/chrome";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as FloorScreen from "@pos_restaurant/../tests/tours/utils/floor_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as ProductScreenPos from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as ProductScreenResto from "@pos_restaurant/../tests/tours/utils/product_screen_util";
import * as TicketScreen from "@point_of_sale/../tests/pos/tours/utils/ticket_screen_util";
import { registry } from "@web/core/registry";

const Chrome = { ...ChromePos, ...ChromeRestaurant };
const ProductScreen = { ...ProductScreenPos, ...ProductScreenResto };

registry.category("web_tour.tours").add("OnlinePaymentWithMultiTables", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("2"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.clickPayButton(),
            PaymentScreen.totalIs("2.20"),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.clickPayButton(),
            PaymentScreen.validateButtonIsHighlighted(true),
            PaymentScreen.clickValidate(),
        ].flat(),
});

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
            TicketScreen.checkStatus("Self-order", "Ongoing"),
            TicketScreen.selectOrder("Self-order"),
            ProductScreen.clickReview(),
            ProductScreen.orderlineIsToOrder("Fanta"),
        ].flat(),
});
