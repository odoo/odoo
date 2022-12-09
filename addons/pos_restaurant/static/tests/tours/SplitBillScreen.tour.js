/** @odoo-module */

import { PaymentScreen } from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";
import { Chrome } from "@pos_restaurant/../tests/tours/helpers/ChromeTourMethods";
import { FloorScreen } from "@pos_restaurant/../tests/tours/helpers/FloorScreenTourMethods";
import { ProductScreen } from "@pos_restaurant/../tests/tours/helpers/ProductScreenTourMethods";
import { SplitBillScreen } from "@pos_restaurant/../tests/tours/helpers/SplitBillScreenTourMethods";
import { TicketScreen } from "@point_of_sale/../tests/tours/helpers/TicketScreenTourMethods";
import { getSteps, startSteps } from "@point_of_sale/../tests/tours/helpers/utils";
import Tour from "web_tour.tour";

// signal to start generating steps
// when finished, steps can be taken from getSteps
startSteps();

FloorScreen.do.clickTable("T2");
ProductScreen.do.confirmOpeningPopup();
ProductScreen.exec.addOrderline("Water", "5", "2", "10.0");
ProductScreen.exec.addOrderline("Minute Maid", "3", "2", "6.0");
ProductScreen.exec.addOrderline("Coca-Cola", "1", "2", "2.0");
ProductScreen.do.clickSplitBillButton();

// Check if the screen contains all the orderlines
SplitBillScreen.check.orderlineHas("Water", "5", "0");
SplitBillScreen.check.orderlineHas("Minute Maid", "3", "0");
SplitBillScreen.check.orderlineHas("Coca-Cola", "1", "0");

// split 3 water and 1 coca-cola
SplitBillScreen.do.clickOrderline("Water");
SplitBillScreen.check.orderlineHas("Water", "5", "1");
SplitBillScreen.do.clickOrderline("Water");
SplitBillScreen.do.clickOrderline("Water");
SplitBillScreen.check.orderlineHas("Water", "5", "3");
SplitBillScreen.check.subtotalIs("6.0");
SplitBillScreen.do.clickOrderline("Coca-Cola");
SplitBillScreen.check.orderlineHas("Coca-Cola", "1", "1");
SplitBillScreen.check.subtotalIs("8.0");

// click pay to split, go back to check the lines
SplitBillScreen.do.clickPay();
PaymentScreen.do.clickBack();
ProductScreen.do.clickOrderline("Water", "3.0");
ProductScreen.do.clickOrderline("Coca-Cola", "1.0");

// go back to the original order and see if the order is changed
Chrome.do.clickTicketButton();
TicketScreen.do.selectOrder("-0001");
ProductScreen.check.isShown();
ProductScreen.do.clickOrderline("Water", "2.0");
ProductScreen.do.clickOrderline("Minute Maid", "3.0");

Tour.register("SplitBillScreenTour", { test: true, url: "/pos/ui" }, getSteps());

startSteps();

FloorScreen.do.clickTable("T2");
ProductScreen.exec.addOrderline("Water", "1", "2.0");
ProductScreen.exec.addOrderline("Minute Maid", "1", "2.0");
ProductScreen.exec.addOrderline("Coca-Cola", "1", "2.0");
Chrome.do.backToFloor();
FloorScreen.do.clickTable("T2");
ProductScreen.do.clickSplitBillButton();

SplitBillScreen.do.clickOrderline("Water");
SplitBillScreen.do.clickOrderline("Coca-Cola");
SplitBillScreen.do.clickPay();
PaymentScreen.do.clickBack();
Chrome.do.clickTicketButton();
TicketScreen.do.selectOrder("-0002");
ProductScreen.do.clickOrderline("Water", "1.0");
ProductScreen.do.clickOrderline("Coca-Cola", "1.0");
ProductScreen.check.totalAmountIs("4.40");
Chrome.do.clickTicketButton();
TicketScreen.do.selectOrder("-0001");
ProductScreen.do.clickOrderline("Minute Maid", "1.0");
ProductScreen.check.totalAmountIs("2.20");

Tour.register("SplitBillScreenTour2", { test: true, url: "/pos/ui" }, getSteps());
