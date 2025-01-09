import * as FloorScreen from "@pos_restaurant/../tests/tours/utils/floor_screen_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as NumberPopup from "@point_of_sale/../tests/tours/utils/number_popup_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as ProductScreenPos from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as ProductScreenResto from "@pos_restaurant/../tests/tours/utils/product_screen_util";
import * as Utils from "@point_of_sale/../tests/tours/utils/common";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/utils/receipt_screen_util";
const ProductScreen = { ...ProductScreenPos, ...ProductScreenResto };
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("FloorScreenTour", {
    test: true,
    steps: () =>
        [
            // check floors if they contain their corresponding tables
            FloorScreen.selectedFloorIs("Main Floor"),
            FloorScreen.hasTable("2"),
            FloorScreen.hasTable("4"),
            FloorScreen.hasTable("5"),
            FloorScreen.clickFloor("Second Floor"),
            FloorScreen.hasTable("3"),
            FloorScreen.hasTable("1"),

            // clicking table in active mode does not open product screen
            // instead, table is selected
            Chrome.clickMenuOption("Edit Plan"),
            FloorScreen.clickTable("3"),
            FloorScreen.selectedTableIs("3"),
            FloorScreen.clickTable("1"),
            FloorScreen.selectedTableIs("1"),

            //test copy floor
            FloorScreen.clickFloor("Main Floor"),
            FloorScreen.clickEditButton("Copy"),
            FloorScreen.selectedFloorIs("Main Floor (copy)"),
            FloorScreen.hasTable("2"),
            FloorScreen.hasTable("4"),
            FloorScreen.hasTable("5"),
            Utils.refresh(),
            Chrome.clickMenuOption("Edit Plan"),
            FloorScreen.clickFloor("Main Floor (copy)"),
            FloorScreen.hasTable("2"),
            FloorScreen.hasTable("4"),
            FloorScreen.hasTable("5"),
            FloorScreen.clickEditButton("Delete"),
            Dialog.confirm(),
            Utils.refresh(),
            Chrome.clickMenuOption("Edit Plan"),
            Utils.elementDoesNotExist(
                ".floor-selector .button-floor:contains('Main Floor (copy)')"
            ),

            // test add table
            FloorScreen.clickFloor("Main Floor"),
            FloorScreen.clickEditButton("Add"),
            FloorScreen.selectedTableIs("1"),
            FloorScreen.clickEditButton("Rename"),

            NumberPopup.enterValue("100"),
            NumberPopup.isShown("100"),
            Dialog.confirm(),
            FloorScreen.clickTable("100"),
            FloorScreen.selectedTableIs("100"),

            // test duplicate table
            FloorScreen.clickEditButton("Copy"),
            // the name is the first number available on the floor
            FloorScreen.selectedTableIs("1"),
            FloorScreen.clickEditButton("Rename"),

            NumberPopup.enterValue("1111"),
            NumberPopup.isShown("1111"),
            Dialog.confirm(),
            FloorScreen.clickTable("1111"),
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
            FloorScreen.clickEditButton("Copy"),
            FloorScreen.selectedTableIs("2"),
            FloorScreen.selectedTableIs("4"),

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
            FloorScreen.clickTable("4"),
            FloorScreen.selectedTableIs("4"),
            FloorScreen.clickEditButton("Seats"),
            NumberPopup.enterValue("15"),
            NumberPopup.isShown("15"),
            Dialog.confirm(),
            FloorScreen.table({ name: "4" }),

            // change shape
            FloorScreen.clickTable("4"),
            FloorScreen.clickEditButton("MakeRound"),

            // Opening product screen in main floor should go back to main floor
            FloorScreen.clickSaveEditButton(),
            FloorScreen.table({ name: "4", withoutClass: ".selected" }),
            FloorScreen.clickTable("4"),
            ProductScreen.isShown(),
            ProductScreen.back(),

            // Opening product screen in second floor should go back to second floor
            FloorScreen.clickFloor("Second Floor"),
            FloorScreen.hasTable("3"),
            FloorScreen.clickTable("3"),
            ProductScreen.isShown(),
            ProductScreen.back(),
            FloorScreen.selectedFloorIs("Second Floor"),

            // Check the linking of tables
            FloorScreen.clickFloor("Main Floor"),
            FloorScreen.clickTable("4"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.back(),
            FloorScreen.isShown(),
            FloorScreen.linkTables("5", "4"),
            FloorScreen.isChildTable("5"),
            Utils.refresh(),
            FloorScreen.isChildTable("5"),

            // Check that tables are unlinked automatically when the order is done
            FloorScreen.clickTable("5"),
            ProductScreen.tableNameShown("4 & 5"),
            ProductScreen.selectedOrderlineHas("Coca-Cola", "1.0"),
            ProductScreen.back(),
            FloorScreen.isShown(),
            FloorScreen.goTo("5"),
            ProductScreen.tableNameShown("4 & 5"),
            ProductScreen.selectedOrderlineHas("Coca-Cola", "1.0"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickNextOrder(),
            Utils.negateStep(FloorScreen.isChildTable("5")),

            FloorScreen.linkTables("5", "4"),
            // Check that the tables are unlinked when the child table is dragged
            {
                content: "Drag table 5 to the bottom of the screen to unlink it",
                trigger: FloorScreen.table({ name: "5" }).trigger,
                async run(helpers) {
                    await helpers.drag_and_drop(`div.floor-map`, {
                        position: {
                            bottom: 0,
                        },
                        relative: true,
                    });
                },
            },
            Utils.negateStep(FloorScreen.isChildTable("5")),
        ].flat(),
});
