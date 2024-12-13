import * as FloorScreen from "@pos_restaurant/../tests/tours/utils/floor_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as NumberPopup from "@point_of_sale/../tests/generic_helpers/number_popup_util";
import * as ChromePos from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as ChromeRestaurant from "@pos_restaurant/../tests/tours/utils/chrome";
const Chrome = { ...ChromePos, ...ChromeRestaurant };
import * as ProductScreenPos from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as ProductScreenResto from "@pos_restaurant/../tests/tours/utils/product_screen_util";
import * as Utils from "@point_of_sale/../tests/generic_helpers/utils";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
const ProductScreen = { ...ProductScreenPos, ...ProductScreenResto };
import { registry } from "@web/core/registry";
import { inLeftSide } from "@point_of_sale/../tests/pos/tours/utils/common";

registry.category("web_tour.tours").add("FloorScreenTour", {
    steps: () =>
        [
            // check floors if they contain their corresponding tables
            Chrome.startPoS(),
            FloorScreen.selectedFloorIs("Main Floor"),
            FloorScreen.hasTable("102"),
            FloorScreen.hasTable("104"),
            FloorScreen.hasTable("105"),
            FloorScreen.clickFloor("Second Floor"),
            FloorScreen.hasTable("203"),
            FloorScreen.hasTable("201"),

            // clicking table in active mode does not open product screen
            // instead, table is selected
            Chrome.clickMenuOption("Edit Plan"),
            FloorScreen.clickTable("203"),
            FloorScreen.selectedTableIs("203"),
            FloorScreen.clickTable("201"),
            FloorScreen.selectedTableIs("201"),

            //test copy floor
            FloorScreen.clickFloor("Main Floor"),
            FloorScreen.clickEditButton("Clone"),
            FloorScreen.selectedFloorIs("Main Floor (copy)"),
            FloorScreen.hasTable("102"),
            FloorScreen.hasTable("104"),
            FloorScreen.hasTable("105"),
            Utils.refresh(),
            Chrome.clickMenuOption("Edit Plan"),
            FloorScreen.clickFloor("Main Floor (copy)"),
            FloorScreen.hasTable("102"),
            FloorScreen.hasTable("104"),
            FloorScreen.hasTable("105"),
            FloorScreen.clickEditButton("Delete"),
            Dialog.confirm(),
            Utils.refresh(),
            Chrome.clickMenuOption("Edit Plan"),
            Utils.elementDoesNotExist(
                ".floor-selector .button-floor:contains('Main Floor (copy)')"
            ),

            // test add table
            FloorScreen.clickFloor("Main Floor"),
            {
                trigger: `.edit-buttons i[aria-label="Add Table"]`,
                run: "click",
            },
            FloorScreen.selectedTableIs("101"),
            FloorScreen.clickEditButton("Rename"),

            NumberPopup.enterValue("100"),
            NumberPopup.isShown("100"),
            Dialog.confirm(),
            FloorScreen.selectedTableIs("100"),

            // test duplicate table
            FloorScreen.clickEditButton("Clone"),
            // the name is the first number available on the floor
            FloorScreen.selectedTableIs("100"),
            FloorScreen.clickEditButton("Rename"),

            NumberPopup.enterValue("1111"),
            NumberPopup.isShown("1111"),
            Dialog.confirm(),
            FloorScreen.selectedTableIs("1111"),

            // switch floor, switch back and check if
            // the new tables are still there
            FloorScreen.clickFloor("Second Floor"),
            FloorScreen.hasTable("203"),
            FloorScreen.hasTable("201"),

            //test duplicate multiple tables
            FloorScreen.clickTable("201"),
            FloorScreen.selectedTableIs("201"),
            FloorScreen.ctrlClickTable("203"),
            FloorScreen.selectedTableIs("203"),
            FloorScreen.clickEditButton("Clone"),
            FloorScreen.selectedTableIs("201"),
            FloorScreen.selectedTableIs("203"),

            //test delete multiple tables
            FloorScreen.clickEditButton("Delete"),
            Dialog.confirm(),

            FloorScreen.clickFloor("Main Floor"),
            FloorScreen.hasTable("102"),
            FloorScreen.hasTable("104"),
            FloorScreen.hasTable("105"),
            FloorScreen.hasTable("100"),
            FloorScreen.hasTable("1111"),

            // test delete table
            FloorScreen.clickTable("1111"),
            FloorScreen.selectedTableIs("1111"),
            FloorScreen.clickEditButton("Delete"),
            Dialog.confirm(),

            // change number of seats
            FloorScreen.clickTable("104"),
            FloorScreen.selectedTableIs("104"),
            FloorScreen.clickEditButton("Seats"),
            NumberPopup.enterValue("⌫9"),
            NumberPopup.enterValue("9"),
            NumberPopup.isShown("9"),
            Dialog.confirm(),
            FloorScreen.table({ name: "104" }),

            // change number of seat when the input is already selected
            FloorScreen.selectedTableIs("104"),
            FloorScreen.clickEditButton("Seats"),
            NumberPopup.enterValue("15"),
            NumberPopup.isShown("15"),
            Dialog.confirm(),
            FloorScreen.table({ name: "104" }),

            // change shape
            FloorScreen.clickEditButton("Make Round"),

            // Opening product screen in main floor should go back to main floor
            FloorScreen.clickSaveEditButton(),
            FloorScreen.table({ name: "104", withoutClass: ".selected" }),
            FloorScreen.clickTable("104"),
            ProductScreen.isShown(),
            Chrome.clickPlanButton(),

            // Opening product screen in second floor should go back to second floor
            FloorScreen.clickFloor("Second Floor"),
            FloorScreen.hasTable("203"),
            FloorScreen.clickTable("203"),
            ProductScreen.isShown(),
            Chrome.clickPlanButton(),
            FloorScreen.selectedFloorIs("Second Floor"),
        ].flat(),
});
registry.category("web_tour.tours").add("TableMergeUnmergeTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            // Check the linking of tables
            FloorScreen.clickFloor("Main Floor"),
            FloorScreen.clickTable("104"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            Chrome.clickPlanButton(),
            FloorScreen.isShown(),
            FloorScreen.linkTables("105", "104"),
            FloorScreen.isChildTable("105"),
            Utils.refresh(),
            FloorScreen.isChildTable("105"),

            // Check that tables are unlinked automatically when the order is done
            FloorScreen.clickTable("105"),
            Chrome.isTabActive("104 & 105"),
            inLeftSide(ProductScreen.orderLineHas("Coca-Cola", "1")),
            Chrome.clickPlanButton(),
            FloorScreen.isShown(),
            FloorScreen.goTo("105"),
            Chrome.isTabActive("104 & 105"),
            inLeftSide(ProductScreen.orderLineHas("Coca-Cola", "1")),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            {
                ...Dialog.confirm(),
                content:
                    "acknowledge printing error ( because we don't have printer in the test. )",
            },
            ReceiptScreen.clickNextOrder(),
            Utils.negateStep(FloorScreen.isChildTable("105")),

            FloorScreen.linkTables("105", "104"),
            // Check that the tables are unlinked when the child table is dragged
            FloorScreen.unlinkTables("105", "104"),
            Utils.negateStep(FloorScreen.isChildTable("105")),

            // Verify that tables are unlinked and original orders are restored after dragging a child table.
            FloorScreen.isShown(),
            FloorScreen.clickTable("104"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            Chrome.clickPlanButton(),
            FloorScreen.isShown(),

            FloorScreen.clickTable("105"),
            ProductScreen.clickDisplayedProduct("Minute Maid"),
            Chrome.clickPlanButton(),
            FloorScreen.isShown(),

            // Link tables 105 and 104
            FloorScreen.linkTables("105", "104"),
            FloorScreen.isChildTable("105"),

            // Check merged orders
            FloorScreen.clickTable("105"),
            Chrome.isTabActive("104 & 105"),
            inLeftSide(ProductScreen.orderLineHas("Coca-Cola", "1")),
            inLeftSide(ProductScreen.orderLineHas("Minute Maid", "1")),
            Chrome.clickPlanButton(),
            FloorScreen.isShown(),

            // Unlink tables and verify restoration of original orders
            FloorScreen.unlinkTables("105", "104"),
            Utils.negateStep(FloorScreen.isChildTable("105")),

            // Check original orders for table 104
            FloorScreen.clickTable("104"),
            inLeftSide(ProductScreen.orderLineHas("Coca-Cola", "1")),
            ProductScreen.clickOrderButton(),
            {
                ...Dialog.confirm(),
                content: "Acknowledge printing error (test does not use a printer).",
            },
            ProductScreen.orderlinesHaveNoChange(),
            Chrome.clickPlanButton(),
            FloorScreen.isShown(),

            // Check original orders for table 105
            FloorScreen.clickTable("105"),
            inLeftSide(ProductScreen.orderLineHas("Minute Maid", "1")),
            ProductScreen.clickOrderButton(),
            {
                ...Dialog.confirm(),
                content: "Acknowledge printing error (test does not use a printer).",
            },
            ProductScreen.orderlinesHaveNoChange(),
            Chrome.clickPlanButton(),
            FloorScreen.isShown(),

            // Relink tables and verify
            FloorScreen.linkTables("105", "104"),
            FloorScreen.clickTable("105"),
            Chrome.isTabActive("104 & 105"),
            ProductScreen.orderlinesHaveNoChange(),

            // Add a new product to the merged order
            ProductScreen.clickDisplayedProduct("Minute Maid"),
            ProductScreen.orderlineIsToOrder("Minute Maid"),
            ProductScreen.clickOrderButton(),
            {
                ...Dialog.confirm(),
                content: "Acknowledge printing error (test does not use a printer).",
            },
            ProductScreen.orderlinesHaveNoChange(),

            // Unlink tables again and verify restoration
            Chrome.clickPlanButton(),
            FloorScreen.isShown(),
            FloorScreen.unlinkTables("105", "104"),
            Utils.negateStep(FloorScreen.isChildTable("105")),

            // Verify orders after unlinking
            FloorScreen.clickTable("105"),
            inLeftSide(ProductScreen.orderLineHas("Minute Maid", "1")),
            Chrome.clickPlanButton(),
            FloorScreen.isShown(),
            FloorScreen.clickTable("104"),
            inLeftSide(ProductScreen.orderLineHas("Coca-Cola", "1")),
            inLeftSide(ProductScreen.orderLineHas("Minute Maid", "1")),
            Chrome.clickPlanButton(),
            FloorScreen.isShown(),
        ].flat(),
});
