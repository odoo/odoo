import * as FloorScreen from "@pos_restaurant/../tests/tours/utils/floor_screen_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as TextInputPopup from "@point_of_sale/../tests/tours/utils/text_input_popup_util";
import * as NumberPopup from "@point_of_sale/../tests/tours/utils/number_popup_util";
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
            Dialog.confirm(),
            // check floors if they contain their corresponding tables
            FloorScreen.selectedFloorIs("Main Floor"),
            FloorScreen.hasTable("2"),
            FloorScreen.hasTable("4"),
            FloorScreen.hasTable("5"),
            FloorScreen.clickFloor("Second Floor"),
            FloorScreen.hasTable("3"),
            FloorScreen.hasTable("1"),

            //test copy floor
            FloorScreen.clickFloor("Main Floor"),
            FloorScreen.clickEditButton("Duplicate"),
            FloorScreen.selectedFloorIs("Main Floor (copy)"),
            FloorScreen.hasTable("2"),
            FloorScreen.hasTable("4"),
            FloorScreen.hasTable("5"),
            Utils.refresh(),
            FloorScreen.clickFloor("Main Floor (copy)"),
            FloorScreen.hasTable("2"),
            FloorScreen.hasTable("4"),
            FloorScreen.hasTable("5"),
            FloorScreen.clickEditButton("Delete"),
            Dialog.confirm(),
            Utils.refresh(),
            Utils.elementDoesNotExist(
                ".floor-selector .button-floor:contains('Main Floor (copy)')"
            ),

            // test add table
            FloorScreen.clickFloor("Main Floor"),
            FloorScreen.add("Table"),
            FloorScreen.editTable("1", "Rename"),

            TextInputPopup.inputText("100"),
            // pressing enter should confirm the text input popup
            { trigger: "textarea", run: "press Enter", in_modal: true },

            // test duplicate table
            FloorScreen.editTable("100", "Duplicate"),
            // the name is the first number available on the floor; in this case, 1
            FloorScreen.editTable("1", "Rename"),

            TextInputPopup.inputText("1111"),
            Dialog.confirm(),
            FloorScreen.hasTable("1111"),

            // switch floor, switch back and check if
            // the new tables are still there
            FloorScreen.clickFloor("Second Floor"),
            FloorScreen.hasTable("3"),
            FloorScreen.hasTable("1"),

            FloorScreen.clickFloor("Main Floor"),
            FloorScreen.hasTable("2"),
            FloorScreen.hasTable("4"),
            FloorScreen.hasTable("5"),
            FloorScreen.hasTable("100"),
            FloorScreen.hasTable("1111"),

            // test delete table
            FloorScreen.editTable("1111", "Delete"),
            Dialog.confirm(),

            // change number of seats
            FloorScreen.editTable("4", "Seats"),
            NumberPopup.enterValue("⌫9"),
            NumberPopup.enterValue("9"),
            NumberPopup.isShown("9"),
            Dialog.confirm(),
            FloorScreen.table({ name: "4", numOfSeats: "9" }),

            // change number of seat when the input is already selected
            FloorScreen.editTable("4", "Seats"),
            NumberPopup.enterValue("15"),
            NumberPopup.isShown("15"),
            Dialog.confirm(),
            FloorScreen.table({ name: "4", numOfSeats: "15" }),

            // change shape
            FloorScreen.editTable("4", "Shape"),

            // Opening product screen in main floor should go back to main floor
            FloorScreen.table({ name: "4", withoutClass: ".selected" }),
            FloorScreen.clickTable("4"),
            ProductScreen.isShown(),
            ProductScreen.back(),
            FloorScreen.selectedFloorIs("Main Floor"),

            // Opening product screen in second floor should go back to second floor
            FloorScreen.clickFloor("Second Floor"),
            FloorScreen.clickTable("3"),
            ProductScreen.isShown(),
            ProductScreen.back(),
            FloorScreen.selectedFloorIs("Second Floor"),

            // Check the linking of tables
            FloorScreen.clickFloor("Main Floor"),
            FloorScreen.linkTables("5", "4"),
            FloorScreen.isChildTable("5"),
            Utils.refresh(),
            FloorScreen.isChildTable("5"),

            // Check that tables are unlinked automatically when the order is done
            FloorScreen.clickTable("5"),
            ProductScreen.tableNameShown("4"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            {
                ...Dialog.confirm(),
                content:
                    "acknowledge printing error ( because we don't have printer in the test. )",
            },
            ReceiptScreen.clickNextOrder(),
            Utils.negateStep(FloorScreen.isChildTable("5")),

            // Check unlinking by dropdown
            FloorScreen.linkTables("5", "4"),
            FloorScreen.editTable("5", "Unlink"),
            Utils.negateStep(FloorScreen.isChildTable("5")),

            // Check that the tables are unlinked when the child table is dragged
            FloorScreen.linkTables("5", "4"),
            {
                content: "Drag table 5 to the bottom of the screen to unlink it",
                trigger: FloorScreen.table({ name: "5" }).trigger,
                async run(helpers) {
                    helpers.delay = 500;
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
