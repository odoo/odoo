import * as ProductScreenPos from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as ProductScreenResto from "@pos_restaurant/../tests/tours/utils/product_screen_util";
const ProductScreen = { ...ProductScreenPos, ...ProductScreenResto };
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as FloorScreen from "@pos_restaurant/../tests/tours/utils/floor_screen_util";
import * as TicketScreen from "@point_of_sale/../tests/tours/utils/ticket_screen_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import { registry } from "@web/core/registry";
import * as DeviceSynchronization from "@pos_restaurant/../tests/tours/utils/devices_synchronization";

registry.category("web_tour.tours").add("PosResTicketScreenTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            // New Ticket button should not be in the ticket screen if no table is selected.
            Chrome.clickMenuOption("Orders"),
            TicketScreen.noNewTicketButton(),
            TicketScreen.clickDiscard(),

            // Make sure that order is deleted properly.
            FloorScreen.clickTable("5"),
            ProductScreen.addOrderline("Minute Maid", "1", "3"),
            ProductScreen.totalAmountIs("3.0"),
            Chrome.clickPlanButton(),
            FloorScreen.orderCountSyncedInTableIs("5", "1"),
            Chrome.clickMenuOption("Orders"),
            TicketScreen.deleteOrder("-0001"),
            Dialog.confirm(),
            Chrome.clickPlanButton(),
            FloorScreen.isShown(),
            FloorScreen.clickTable("5"),
            ProductScreen.orderIsEmpty(),
        ].flat(),
});

registry.category("web_tour.tours").add("OrderNumberConflictTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            FloorScreen.clickTable("3"),
            ProductScreen.isShown(),
            ProductScreen.addOrderline("Coca-Cola", "1", "3"),
            Chrome.clickPlanButton(),
            Chrome.clickMenuOption("Orders"),
            TicketScreen.nthColumnContains(1, 2, "Order"),
            TicketScreen.nthColumnContains(1, 3, "1"),
            TicketScreen.nthColumnContains(2, 2, "Self-Order"),
            TicketScreen.nthColumnContains(2, 3, "S"),
            TicketScreen.nthColumnContains(2, 3, "1"),
        ].flat(),
});

registry.category("web_tour.tours").add("test_cancel_order_from_ui", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.isShown(),
            ProductScreen.addOrderline("Coca-Cola", "1", "3"),
            Chrome.clickPlanButton(),
            Chrome.isSynced(),
            FloorScreen.isShown(),
            FloorScreen.clickTable("5"),
            ProductScreen.clickReview(),
            ProductScreen.clickControlButton("Cancel Order"),
            Dialog.confirm(),
            FloorScreen.isShown(),
            Chrome.clickMenuOption("Orders"),
            TicketScreen.noOrderIsThere(),
            TicketScreen.selectFilter("Paid"),
            TicketScreen.noOrderIsThere(),
            Chrome.storedOrderCount(0),
        ].flat(),
});

registry.category("web_tour.tours").add("OrderSynchronisationTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            DeviceSynchronization.createNewOrderOnTable("4", [
                ["Coca-Cola", 50],
                ["Water", 30],
            ]),
            FloorScreen.clickTable("4"),
            ProductScreen.orderLineHas("Coca-Cola", "50.0"),
            DeviceSynchronization.markOrderAsPaid(),
            ProductScreen.isShown(),
            Chrome.clickMenuOption("Orders"),
            TicketScreen.selectFilter("Paid"),
            TicketScreen.checkStatus("device_sync", "Paid"),
            TicketScreen.selectOrder("device_sync"),
            TicketScreen.confirmRefund(),
        ].flat(),
});
