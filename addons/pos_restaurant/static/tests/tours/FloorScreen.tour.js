/** @odoo-module */

import { Chrome } from "@pos_restaurant/../tests/tours/helpers/ChromeTourMethods";
import { FloorScreen } from "@pos_restaurant/../tests/tours/helpers/FloorScreenTourMethods";
import { TextInputPopup } from "@point_of_sale/../tests/tours/helpers/TextInputPopupTourMethods";
import { NumberPopup } from "@point_of_sale/../tests/tours/helpers/NumberPopupTourMethods";
import { ProductScreen } from "@pos_restaurant/../tests/tours/helpers/ProductScreenTourMethods";
import { getSteps, startSteps } from "@point_of_sale/../tests/tours/helpers/utils";
import { registry } from "@web/core/registry";

// signal to start generating steps
// when finished, steps can be taken from getSteps
startSteps();

// check floors if they contain their corresponding tables
FloorScreen.check.selectedFloorIs("Main Floor");
FloorScreen.check.hasTable("2");
FloorScreen.check.hasTable("4");
FloorScreen.check.hasTable("5");
FloorScreen.do.clickFloor("Second Floor");
FloorScreen.check.hasTable("3");
FloorScreen.check.hasTable("1");

// clicking table in active mode does not open product screen
// instead, table is selected
FloorScreen.do.clickEdit();
FloorScreen.check.editModeIsActive(true);
FloorScreen.do.clickTable("3");
FloorScreen.check.selectedTableIs("3");
FloorScreen.do.clickTable("1");
FloorScreen.check.selectedTableIs("1");

// switching floor in edit mode deactivates edit mode
FloorScreen.do.clickFloor("Main Floor");
FloorScreen.check.editModeIsActive(false);
FloorScreen.do.clickEdit();
FloorScreen.check.editModeIsActive(true);

// test add table
FloorScreen.do.clickAddTable();
FloorScreen.check.selectedTableIs("1");
FloorScreen.do.clickRename();
TextInputPopup.check.isShown();
TextInputPopup.do.inputText("100");
TextInputPopup.do.clickConfirm();
FloorScreen.check.selectedTableIs("100");

// test duplicate table
FloorScreen.do.clickDuplicate();
// new table is already named 101
FloorScreen.check.selectedTableIs("101");
FloorScreen.do.clickRename();
TextInputPopup.check.isShown();
TextInputPopup.do.inputText("1111");
TextInputPopup.do.clickConfirm();
FloorScreen.check.selectedTableIs("1111");

// switch floor, switch back and check if
// the new tables are still there
FloorScreen.do.clickFloor("Second Floor");
FloorScreen.check.editModeIsActive(false);
FloorScreen.check.hasTable("3");
FloorScreen.check.hasTable("1");

FloorScreen.do.clickFloor("Main Floor");
FloorScreen.check.hasTable("2");
FloorScreen.check.hasTable("4");
FloorScreen.check.hasTable("5");
FloorScreen.check.hasTable("100");
FloorScreen.check.hasTable("1111");

// test delete table
FloorScreen.do.clickEdit();
FloorScreen.check.editModeIsActive(true);
FloorScreen.do.clickTable("2");
FloorScreen.check.selectedTableIs("2");
FloorScreen.do.clickTrash();
Chrome.do.confirmPopup();

// change number of seats
FloorScreen.do.clickTable("4");
FloorScreen.check.selectedTableIs("4");
FloorScreen.do.clickSeats();
NumberPopup.do.pressNumpad("Backspace 9");
NumberPopup.check.inputShownIs("9");
NumberPopup.do.clickConfirm();
FloorScreen.check.tableSeatIs("4", "9");

// change number of seat when the input is already selected
FloorScreen.do.clickTable("4");
FloorScreen.check.selectedTableIs("4");
FloorScreen.do.clickSeats();
NumberPopup.do.pressNumpad("1 5");
NumberPopup.check.inputShownIs("15");
NumberPopup.do.clickConfirm();
FloorScreen.check.tableSeatIs("4", "15");

// change shape
FloorScreen.do.changeShapeTo("round");

// Opening product screen in main floor should go back to main floor
FloorScreen.do.clickEdit();
FloorScreen.check.editModeIsActive(false);
FloorScreen.check.tableIsNotSelected("4");
FloorScreen.do.clickTable("4");
ProductScreen.check.isShown();
Chrome.check.backToFloorTextIs("Main Floor", "4");
Chrome.do.backToFloor();

// Opening product screen in second floor should go back to second floor
FloorScreen.do.clickFloor("Second Floor");
FloorScreen.check.hasTable("3");
FloorScreen.do.clickTable("3");
Chrome.check.backToFloorTextIs("Second Floor", "3");

registry.category("web_tour.tours").add("FloorScreenTour", { test: true, url: "/pos/ui", steps: getSteps() });
