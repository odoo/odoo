import * as ProductScreenPos from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as ProductScreenResto from "@pos_restaurant/../tests/tours/utils/product_screen_util";
const ProductScreen = { ...ProductScreenPos, ...ProductScreenResto };
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as FloorScreen from "@pos_restaurant/../tests/tours/utils/floor_screen_util";
import * as TicketScreen from "@point_of_sale/../tests/pos/tours/utils/ticket_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import { registry } from "@web/core/registry";

const { DateTime } = luxon;

registry.category("web_tour.tours").add("PosResTicketScreenTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            // New Ticket button should not be in the ticket screen if no table is selected.
            Chrome.clickOrders(),
            Chrome.clickPlanButton(),

            // Make sure that order is deleted properly.
            FloorScreen.clickTable("5"),
            ProductScreen.addOrderline("Minute Maid", "1", "3"),
            ProductScreen.totalAmountIs("3.0"),
            Chrome.clickPlanButton(),
            FloorScreen.orderCountSyncedInTableIs("5", 0),
            Chrome.clickOrders(),
            TicketScreen.deleteOrder("001"),
            Dialog.confirm(),
            Chrome.clickPlanButton(),
            FloorScreen.isShown(),
            FloorScreen.clickTable("5"),
            ProductScreen.orderIsEmpty(),
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
            Chrome.clickOrders(),
            TicketScreen.noOrderIsThere(),
            TicketScreen.selectFilter("Paid"),
            TicketScreen.noOrderIsThere(),
            Chrome.storedOrderCount(0),
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
            Chrome.clickOrders(),
            TicketScreen.nthRowContains(1, `${String(DateTime.now().year).slice(-2)}0`),
            TicketScreen.nthRowContains(1, "T 101"),
            TicketScreen.nthRowContains(2, `${String(DateTime.now().year).slice(-2)}1`),
            TicketScreen.nthRowContains(2, "T 103"),
        ].flat(),
});

registry.category("web_tour.tours").add("test_sync_lines_qty_update_ticket_screen", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            Chrome.clickRegister(),
            ProductScreen.addOrderline("Coca-Cola", "1"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("A powerful Pos man!"),

            Chrome.clickOrders(),
            TicketScreen.selectOrder("001"),
            TicketScreen.loadSelectedOrder(),

            ProductScreen.clickOrderline("Coca-Cola", "1"),
            ProductScreen.clickNumpad("3"),
            ProductScreen.selectedOrderlineHas("Coca-Cola", "3"),
            Chrome.clickOrders(),
        ].flat(),
});
