import * as ProductScreenPos from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as ProductScreenResto from "@pos_restaurant/../tests/tours/utils/product_screen_util";
const ProductScreen = { ...ProductScreenPos, ...ProductScreenResto };
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as FloorScreen from "@pos_restaurant/../tests/tours/utils/floor_screen_util";
import * as TicketScreen from "@point_of_sale/../tests/pos/tours/utils/ticket_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PosResTicketScreenTour", {
    checkDelay: 50,
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            // New Ticket button should not be in the ticket screen if no table is selected.
            Chrome.clickOrders(),
            Chrome.clickPlanButton(),

            // Make sure that order is deleted properly.
            FloorScreen.clickTable("105"),
            ProductScreen.addOrderline("Minute Maid", "1", "3"),
            ProductScreen.totalAmountIs("3.0"),
            Chrome.clickPlanButton(),
            FloorScreen.orderCountSyncedInTableIs("5", "1"),
            Chrome.clickOrders(),
            TicketScreen.deleteOrder("001"),
            Dialog.confirm(),
            Chrome.clickPlanButton(),
            FloorScreen.isShown(),
            FloorScreen.clickTable("105"),
            ProductScreen.orderIsEmpty(),
        ].flat(),
});

registry.category("web_tour.tours").add("OrderNumberConflictTour", {
    checkDelay: 50,
    steps: () =>
        [
            Chrome.startPoS(),
            FloorScreen.clickTable("103"),
            ProductScreen.isShown(),
            ProductScreen.addOrderline("Coca-Cola", "1", "3"),
            Chrome.clickPlanButton(),
            Chrome.clickOrders(),
            TicketScreen.nthRowContains(1, "Self-Order"),
            TicketScreen.nthRowContains(1, "T 101"),
            TicketScreen.nthRowNotContains(2, "Self-Order"),
            TicketScreen.nthRowContains(2, "T 103"),
        ].flat(),
});
