import * as FloorScreen from "@pos_restaurant/../tests/tours/utils/floor_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as ChromePos from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as ChromeRestaurant from "@pos_restaurant/../tests/tours/utils/chrome";
const Chrome = { ...ChromePos, ...ChromeRestaurant };
import * as ProductScreenPos from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as ProductScreenResto from "@pos_restaurant/../tests/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as FeedbackScreen from "@point_of_sale/../tests/pos/tours/utils/feedback_screen_util";
const ProductScreen = { ...ProductScreenPos, ...ProductScreenResto };
import * as TicketScreen from "@point_of_sale/../tests/pos/tours/utils/ticket_screen_util";
import { registry } from "@web/core/registry";

/** TODO Edit floor plan tour
registry.category("web_tour.tours").add("test_create_floor_tour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            Chrome.clickMenuOption("Edit Plan"),
            FloorScreen.addFloor("AAA"),

            // clicking table in active mode does not open product screen
            // instead, table is selected

            Chrome.clickMenuOption("Edit Plan"),
            FloorScreen.clickTable("3"),
            FloorScreen.selectedTableIs("3"),
            FloorScreen.clickTable("1"),
            FloorScreen.selectedTableIs("1"),

            // test add table
            FloorScreen.clickFloor("Main Floor"),
            {
                trigger: `.edit-buttons i[aria-label="Add Table"]`,
                run: "click",
            },
            FloorScreen.selectedTableIs("6"),
            FloorScreen.clickEditButton("Rename"),

            NumberPopup.enterValue("100"),
            NumberPopup.isShown("100"),
            Dialog.confirm(),
            FloorScreen.selectedTableIs("100"),

            // test duplicate table
            FloorScreen.clickEditButton("Clone"),
            // the name is the first number available on the floor
            FloorScreen.selectedTableIs("1"),
            FloorScreen.clickEditButton("Rename"),

            NumberPopup.enterValue("1111"),
            NumberPopup.isShown("1111"),
            Dialog.confirm(),
            FloorScreen.selectedTableIs("1111"),

            // switch floor, switch back and check if
            // the new tables are still there
            FloorScreen.clickFloor("Second Floor"),
            FloorScreen.hasTable("3"),
            FloorScreen.hasTable("1"),

            //test duplicate multiple tables
            FloorScreen.clickTable("1"),
            FloorScreen.selectedTableIs("1"),
            FloorScreen.ctrlClickTable("3"),
            FloorScreen.selectedTableIs("3"),
            FloorScreen.clickEditButton("Clone"),
            FloorScreen.selectedTableIs("4"),
            FloorScreen.selectedTableIs("5"),

            //test delete multiple tables
            FloorScreen.clickEditButton("Delete"),
            Dialog.confirm(),

            FloorScreen.clickFloor("Main Floor"),
            FloorScreen.hasTable("2"),
            FloorScreen.hasTable("4"),
            FloorScreen.hasTable("5"),
            FloorScreen.hasTable("100"),
            FloorScreen.hasTable("1111"),

            // test delete table
            FloorScreen.clickTable("1111"),
            FloorScreen.selectedTableIs("1111"),
            FloorScreen.clickEditButton("Delete"),
            Dialog.confirm(),

            // change number of seats
            FloorScreen.clickTable("4"),
            FloorScreen.selectedTableIs("4"),
            FloorScreen.clickEditButton("Seats"),
            NumberPopup.enterValue("⌫9"),
            NumberPopup.enterValue("9"),
            NumberPopup.isShown("9"),
            Dialog.confirm(),
            FloorScreen.table({ name: "4" }),

            // change number of seat when the input is already selected
            FloorScreen.selectedTableIs("4"),
            FloorScreen.clickEditButton("Seats"),
            NumberPopup.enterValue("15"),
            NumberPopup.isShown("15"),
            Dialog.confirm(),
            FloorScreen.table({ name: "4" }),

            // change shape
            FloorScreen.clickEditButton("Make Round"),

            // Opening product screen in main floor should go back to main floor
            FloorScreen.clickSaveEditButton(),
            FloorScreen.table({ name: "4", withoutClass: ".selected" }),
            FloorScreen.clickTable("4"),
            ProductScreen.isShown(),
            Chrome.clickPlanButton(),
        ].flat(),
});
 **/

registry.category("web_tour.tours").add("test_tax_in_merge_table_order_line_tour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickFloor("Main Floor"),
            FloorScreen.clickTable("4"),
            ProductScreen.clickDisplayedProduct("product_1"),
            Chrome.clickPlanButton(),
            FloorScreen.clickFloor("Main Floor"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("product_2"),
            Chrome.clickPlanButton(),
            FloorScreen.isShown(),
            FloorScreen.linkTables("5", "4"),
            FloorScreen.isChildTable("5"),
        ].flat(),
});

registry.category("web_tour.tours").add("no_ghost_floor", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // 1. Create new floor along with a table
            FloorScreen.clickEditPlan(),
            FloorScreen.addFloor("Ghost Floor"),
            FloorScreen.addTable({ name: "999" }),
            FloorScreen.clickSaveEditButton(),

            // 2. Create and pay an order on that table
            FloorScreen.clickFloor("Ghost Floor"),
            FloorScreen.clickTable("999"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.clickPayButton(false),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.clickNextOrder(),

            // // 3. Delete the floor
            FloorScreen.clickEditPlan(),
            FloorScreen.deleteFloor("Ghost Floor"),
            FloorScreen.clickSaveEditButton(),

            // 4. Refund one orderline of the paid order
            Chrome.clickOrders(),
            TicketScreen.selectFilter("Active"),
            TicketScreen.selectFilter("Paid"),
            TicketScreen.selectOrder("0001"),
            TicketScreen.confirmRefund(),
            PaymentScreen.isShown(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.clickNextOrder(),

            // 5. Floor Plan ===> The floor deleted was reappearing
            FloorScreen.hasNotFloor("Ghost Floor"),
        ].flat(),
});
