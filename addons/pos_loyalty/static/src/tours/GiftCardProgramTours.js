/** @odoo-module **/

import { PosLoyalty } from "@pos_loyalty/tours/PosLoyaltyTourMethods";
import { ProductScreen } from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import { TextInputPopup } from "@point_of_sale/../tests/tours/helpers/TextInputPopupTourMethods";
import { getSteps, startSteps } from "@point_of_sale/../tests/tours/helpers/utils";
import Tour from "web_tour.tour";

//#region GiftCardProgramCreateSetTour1
startSteps();
ProductScreen.do.confirmOpeningPopup();
ProductScreen.do.clickHomeCategory();
ProductScreen.do.clickDisplayedProduct("Gift Card");
PosLoyalty.check.orderTotalIs("50.00");
PosLoyalty.exec.finalizeOrder("Cash", "50");
Tour.register("GiftCardProgramCreateSetTour1", { test: true, url: "/pos/web" }, getSteps());
//#endregion

//#region GiftCardProgramCreateSetTour2
startSteps();
ProductScreen.do.clickHomeCategory();
ProductScreen.do.clickDisplayedProduct("Whiteboard Pen");
PosLoyalty.do.enterCode("044123456");
PosLoyalty.check.orderTotalIs("0.00");
PosLoyalty.exec.finalizeOrder("Cash", "0");
Tour.register("GiftCardProgramCreateSetTour2", { test: true, url: "/pos/web" }, getSteps());
//#endregion

//#region GiftCardProgramScanUseTour
startSteps();
ProductScreen.do.confirmOpeningPopup();
ProductScreen.do.clickHomeCategory();
// Pay the 5$ gift card.
ProductScreen.do.clickDisplayedProduct("Gift Card");
TextInputPopup.check.isShown();
TextInputPopup.do.inputText("044123456");
TextInputPopup.do.clickConfirm();
PosLoyalty.check.orderTotalIs("5.00");
PosLoyalty.exec.finalizeOrder("Cash", "5");
// Partially use the gift card. (4$)
ProductScreen.exec.addOrderline("Desk Pad", "2", "2", "4.0");
PosLoyalty.do.enterCode("044123456");
PosLoyalty.check.orderTotalIs("0.00");
PosLoyalty.exec.finalizeOrder("Cash", "0");
// Use the remaining of the gift card. (5$ - 4$ = 1$)
ProductScreen.exec.addOrderline("Whiteboard Pen", "6", "6", "36.0");
PosLoyalty.do.enterCode("044123456");
PosLoyalty.check.orderTotalIs("35.00");
PosLoyalty.exec.finalizeOrder("Cash", "35");
Tour.register("GiftCardProgramScanUseTour", { test: true, url: "/pos/web" }, getSteps());
//#endregion
