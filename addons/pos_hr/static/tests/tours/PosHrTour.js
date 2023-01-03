/** @odoo-module */

import { PosHr } from "@pos_hr/../tests/tours/PosHrTourMethods";
import { ProductScreen } from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import { TicketScreen } from "@point_of_sale/../tests/tours/helpers/TicketScreenTourMethods";
import { Chrome } from "@point_of_sale/../tests/tours/helpers/ChromeTourMethods";
import { ErrorPopup } from "@point_of_sale/../tests/tours/helpers/ErrorPopupTourMethods";
import { NumberPopup } from "@point_of_sale/../tests/tours/helpers/NumberPopupTourMethods";
import { SelectionPopup } from "@point_of_sale/../tests/tours/helpers/SelectionPopupTourMethods";
import { getSteps, startSteps } from "@point_of_sale/../tests/tours/helpers/utils";
import Tour from "web_tour.tour";

startSteps();

PosHr.check.loginScreenIsShown();
PosHr.do.clickLoginButton();
SelectionPopup.check.isShown();
SelectionPopup.check.hasSelectionItem("Pos Employee1");
SelectionPopup.check.hasSelectionItem("Pos Employee2");
SelectionPopup.check.hasSelectionItem("Mitchell Admin");
SelectionPopup.do.clickItem("Pos Employee1");
NumberPopup.check.isShown();
NumberPopup.do.pressNumpad("2 5");
NumberPopup.check.inputShownIs("••");
NumberPopup.do.pressNumpad("8 1");
NumberPopup.check.inputShownIs("••••");
NumberPopup.do.clickConfirm();
ErrorPopup.check.isShown();
ErrorPopup.do.clickConfirm();
PosHr.do.clickLoginButton();
SelectionPopup.do.clickItem("Pos Employee1");
NumberPopup.check.isShown();
NumberPopup.do.pressNumpad("2 5");
NumberPopup.check.inputShownIs("••");
NumberPopup.do.pressNumpad("8 0");
NumberPopup.check.inputShownIs("••••");
NumberPopup.do.clickConfirm();
ProductScreen.check.isShown();
ProductScreen.do.confirmOpeningPopup();
PosHr.check.cashierNameIs("Pos Employee1");
PosHr.do.clickCashierName();
SelectionPopup.do.clickItem("Mitchell Admin");
PosHr.check.cashierNameIs("Mitchell Admin");
PosHr.do.clickLockButton();
PosHr.do.clickLoginButton();
SelectionPopup.do.clickItem("Pos Employee2");
NumberPopup.do.pressNumpad("1 2");
NumberPopup.check.inputShownIs("••");
NumberPopup.do.pressNumpad("3 4");
NumberPopup.check.inputShownIs("••••");
NumberPopup.do.clickConfirm();
ProductScreen.check.isShown();
ProductScreen.do.clickHomeCategory();

// Create orders and check if the ticket list has the right employee for each order
// order for employee 2
ProductScreen.exec.addOrderline("Desk Pad", "1", "2");
ProductScreen.check.totalAmountIs("2.0");
Chrome.do.clickTicketButton();
TicketScreen.check.nthRowContains(2, "Pos Employee2");

// order for employee 1
PosHr.do.clickLockButton();
PosHr.exec.login("Pos Employee1", "2580");
TicketScreen.do.clickNewTicket();
ProductScreen.exec.addOrderline("Desk Pad", "1", "4");
ProductScreen.check.totalAmountIs("4.0");
Chrome.do.clickTicketButton();
TicketScreen.check.nthRowContains(2, "Pos Employee2");
TicketScreen.check.nthRowContains(3, "Pos Employee1");

// order for admin
PosHr.do.clickCashierName();
SelectionPopup.do.clickItem("Mitchell Admin");
PosHr.check.cashierNameIs("Mitchell Admin");
TicketScreen.do.clickNewTicket();
ProductScreen.exec.addOrderline("Desk Pad", "1", "8");
ProductScreen.check.totalAmountIs("8.0");
Chrome.do.clickTicketButton();
TicketScreen.check.nthRowContains(4, "Mitchell Admin");

Tour.register("PosHrTour", { test: true, url: "/pos/ui" }, getSteps());
