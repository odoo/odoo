import * as ProductScreenPos from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as ProductScreenResto from "@pos_restaurant/../tests/tours/utils/product_screen_util";
const ProductScreen = { ...ProductScreenPos, ...ProductScreenResto };
import * as TicketScreen from "@point_of_sale/../tests/pos/tours/utils/ticket_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_pos_self_order_preparation_changes", {
    steps: () =>
        [
            Chrome.startPoS(),
            Chrome.clickOrders(),
            TicketScreen.checkStatus("Self-order", "Ongoing"),
            TicketScreen.selectOrder("Self-order"),
            TicketScreen.loadSelectedOrder(),
            ProductScreen.isShown(),
            ProductScreen.orderlinesHaveNoChange(),
        ].flat(),
});
