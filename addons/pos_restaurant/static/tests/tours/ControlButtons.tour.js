/** @odoo-module */

import { TextAreaPopup } from "@point_of_sale/../tests/tours/helpers/TextAreaPopupTourMethods";
import { NumberPopup } from "@point_of_sale/../tests/tours/helpers/NumberPopupTourMethods";
import { Chrome } from "@pos_restaurant/../tests/tours/helpers/ChromeTourMethods";
import { FloorScreen } from "@pos_restaurant/../tests/tours/helpers/FloorScreenTourMethods";
import { ProductScreen } from "@pos_restaurant/../tests/tours/helpers/ProductScreenTourMethods";
import { SplitBillScreen } from "@pos_restaurant/../tests/tours/helpers/SplitBillScreenTourMethods";
import { BillScreen } from "@pos_restaurant/../tests/tours/helpers/BillScreenTourMethods";
import { getSteps, startSteps } from "@point_of_sale/../tests/tours/helpers/utils";
import Tour from "web_tour.tour";

// signal to start generating steps
// when finished, steps can be taken from getSteps
startSteps();

// Test TransferOrderButton
FloorScreen.do.clickTable("T2");
ProductScreen.exec.addOrderline("Water", "5", "2", "10.0");
ProductScreen.do.clickTransferButton();
FloorScreen.do.clickTable("T4");
ProductScreen.do.clickOrderline("Water", "5", "2");
Chrome.do.backToFloor();
FloorScreen.do.clickTable("T2");
ProductScreen.check.orderIsEmpty();
Chrome.do.backToFloor();
FloorScreen.do.clickTable("T4");
ProductScreen.do.clickOrderline("Water", "5", "2");

// Test SplitBillButton
ProductScreen.do.clickSplitBillButton();
SplitBillScreen.do.clickBack();

// Test OrderlineNoteButton
ProductScreen.do.clickNoteButton();
TextAreaPopup.check.isShown();
TextAreaPopup.do.inputText("test note");
TextAreaPopup.do.clickConfirm();
ProductScreen.check.orderlineHasNote("Water", "5", "test note");
ProductScreen.exec.addOrderline("Water", "8", "1", "8.0");

// Test PrintBillButton
ProductScreen.do.clickPrintBillButton();
BillScreen.check.isShown();
BillScreen.do.clickOk();

// Test GuestButton
ProductScreen.do.clickGuestButton();
NumberPopup.do.pressNumpad("1 5");
NumberPopup.check.inputShownIs("15");
NumberPopup.do.clickConfirm();
ProductScreen.check.guestNumberIs("15");

ProductScreen.do.clickGuestButton();
NumberPopup.do.pressNumpad("5");
NumberPopup.check.inputShownIs("5");
NumberPopup.do.clickConfirm();
ProductScreen.check.guestNumberIs("5");

Tour.register("ControlButtonsTour", { test: true, url: "/pos/ui" }, getSteps());
