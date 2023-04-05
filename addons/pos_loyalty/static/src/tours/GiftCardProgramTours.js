/** @odoo-module **/

import { PosLoyalty } from "@pos_loyalty/tours/PosLoyaltyTourMethods";
import { ProductScreen } from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import { TextInputPopup } from "@point_of_sale/../tests/tours/helpers/TextInputPopupTourMethods";
import { getSteps, startSteps } from "@point_of_sale/../tests/tours/helpers/utils";
import { registry } from "@web/core/registry";
import { TicketScreen } from "@point_of_sale/../tests/tours/helpers/TicketScreenTourMethods";

//#region GiftCardProgramCreateSetTour1
startSteps();
ProductScreen.do.confirmOpeningPopup();
ProductScreen.do.clickHomeCategory();
ProductScreen.do.clickDisplayedProduct("Gift Card");
PosLoyalty.check.orderTotalIs("50.00");
PosLoyalty.exec.finalizeOrder("Cash", "50");
registry
    .category("web_tour.tours")
    .add("GiftCardProgramCreateSetTour1", { test: true, url: "/pos/web", steps: getSteps() });
//#endregion

//#region GiftCardProgramCreateSetTour2
startSteps();
ProductScreen.do.clickHomeCategory();
ProductScreen.do.clickDisplayedProduct("Whiteboard Pen");
PosLoyalty.do.enterCode("044123456");
PosLoyalty.check.orderTotalIs("0.00");
PosLoyalty.exec.finalizeOrder("Cash", "0");
registry
    .category("web_tour.tours")
    .add("GiftCardProgramCreateSetTour2", { test: true, url: "/pos/web", steps: getSteps() });
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
registry
    .category("web_tour.tours")
    .add("GiftCardProgramScanUseTour", { test: true, url: "/pos/web", steps: getSteps() });
//#endregion

startSteps();
ProductScreen.do.confirmOpeningPopup();
ProductScreen.do.clickHomeCategory();
ProductScreen.exec.addOrderline("Magnetic Board", "1"); // 1.98
PosLoyalty.check.orderTotalIs("1.98");
PosLoyalty.exec.finalizeOrder("Cash", "20");
ProductScreen.do.clickRefund();
TicketScreen.do.selectOrder("-0001");
TicketScreen.do.clickOrderline("Magnetic Board");
TicketScreen.do.pressNumpad("1");
TicketScreen.do.confirmRefund();
ProductScreen.check.isShown();
ProductScreen.check.selectedOrderlineHas("Magnetic Board", "-1.00");
ProductScreen.exec.addOrderline("Gift Card", "1");
ProductScreen.check.selectedOrderlineHas("Gift Card", "1");
PosLoyalty.check.orderTotalIs("0.0");
registry
    .category("web_tour.tours")
    .add("GiftCardWithRefundtTour", { test: true, url: "/pos/web", steps: getSteps() });
