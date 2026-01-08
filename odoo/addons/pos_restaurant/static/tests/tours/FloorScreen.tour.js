/** @odoo-module */

import * as Chrome from "@point_of_sale/../tests/tours/helpers/ChromeTourMethods";
import * as FloorScreen from "@pos_restaurant/../tests/tours/helpers/FloorScreenTourMethods";
import * as TextInputPopup from "@point_of_sale/../tests/tours/helpers/TextInputPopupTourMethods";
import * as NumberPopup from "@point_of_sale/../tests/tours/helpers/NumberPopupTourMethods";
import * as ProductScreenPos from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as ProductScreenResto from "@pos_restaurant/../tests/tours/helpers/ProductScreenTourMethods";
const ProductScreen = { ...ProductScreenPos, ...ProductScreenResto };
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("FloorScreenTour", {
    test: true,
    url: "/pos/ui",
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
            FloorScreen.clickEdit(),
            FloorScreen.clickTable("3"),
            FloorScreen.selectedTableIs("3"),
            FloorScreen.clickTable("1"),
            FloorScreen.selectedTableIs("1"),

            // test add table
            FloorScreen.clickFloor("Main Floor"),
            FloorScreen.clickAddTable(),
            FloorScreen.selectedTableIs("1"),
            FloorScreen.clickRename(),
            TextInputPopup.isShown(),
            TextInputPopup.inputText("100"),
            TextInputPopup.clickConfirm(),
            FloorScreen.clickTable("100"),
            FloorScreen.selectedTableIs("100"),

            // test duplicate table
            FloorScreen.clickDuplicate(),
            // the name is the first number available on the floor
            FloorScreen.selectedTableIs("1"),
            FloorScreen.clickRename(),
            TextInputPopup.isShown(),
            TextInputPopup.inputText("1111"),
            TextInputPopup.clickConfirm(),
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
            FloorScreen.clickDuplicate(),
            FloorScreen.selectedTableIs("2"),
            FloorScreen.selectedTableIs("4"),

            //test delete multiple tables
            FloorScreen.clickTrash(),
            Chrome.confirmPopup(),

            FloorScreen.clickFloor("Main Floor"),
            FloorScreen.hasTable("2"),
            FloorScreen.hasTable("4"),
            FloorScreen.hasTable("5"),
            FloorScreen.hasTable("100"),
            FloorScreen.hasTable("1111"),

            // test delete table
            FloorScreen.clickTable("2"),
            FloorScreen.selectedTableIs("2"),
            FloorScreen.clickTrash(),
            Chrome.confirmPopup(),

            // change number of seats
            FloorScreen.clickTable("4"),
            FloorScreen.selectedTableIs("4"),
            FloorScreen.clickSeats(),
            NumberPopup.pressNumpad("⌫ 9"),
            NumberPopup.fillPopupValue("9"),
            NumberPopup.inputShownIs("9"),
            NumberPopup.clickConfirm(),
            FloorScreen.tableSeatIs("4", "9"),

            // change number of seat when the input is already selected
            FloorScreen.clickTable("4"),
            FloorScreen.selectedTableIs("4"),
            FloorScreen.clickSeats(),
            NumberPopup.enterValue("15"),
            NumberPopup.inputShownIs("15"),
            NumberPopup.clickConfirm(),
            FloorScreen.tableSeatIs("4", "15"),

            // change shape
            FloorScreen.clickTable("4"),
            FloorScreen.changeShapeTo("round"),

            // Opening product screen in main floor should go back to main floor
            FloorScreen.closeEdit(),
            FloorScreen.tableIsNotSelected("4"),
            FloorScreen.clickTable("4"),
            ProductScreen.isShown(),
            FloorScreen.backToFloor(),

            // Opening product screen in second floor should go back to second floor
            FloorScreen.clickFloor("Second Floor"),
            FloorScreen.hasTable("3"),
            FloorScreen.clickTable("3"),
        ].flat(),
});
