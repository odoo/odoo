/** @odoo-module **/

import { PosLoyalty } from 'pos_loyalty.tour.PosCouponTourMethods';
import { ProductScreen } from 'point_of_sale.tour.ProductScreenTourMethods';
import { TextInputPopup } from 'point_of_sale.tour.TextInputPopupTourMethods';
import { getSteps, startSteps } from 'point_of_sale.tour.utils';
import Tour from 'web_tour.tour';

//#region GiftCardProgramCreateSetTour1
startSteps();
ProductScreen.do.confirmOpeningPopup();
ProductScreen.do.clickHomeCategory();
ProductScreen.do.clickDisplayedProduct('Gift Card');
PosLoyalty.check.orderTotalIs('50.00');
PosLoyalty.exec.finalizeOrder('Cash');
Tour.register('GiftCardProgramCreateSetTour1', { test: true, url: '/pos/web' }, getSteps());
//#endregion

//#region GiftCardProgramCreateSetTour2
startSteps();
ProductScreen.do.clickHomeCategory();
ProductScreen.do.clickDisplayedProduct('Whiteboard Pen');
PosLoyalty.do.enterCode('044123456');
PosLoyalty.check.orderTotalIs('0.00');
PosLoyalty.exec.finalizeOrder('Cash');
Tour.register('GiftCardProgramCreateSetTour2', { test: true, url: '/pos/web' }, getSteps());
//#endregion

//#region GiftCardProgramScanUseTour
startSteps();
ProductScreen.do.confirmOpeningPopup();
ProductScreen.do.clickHomeCategory();
// Pay the 5$ gift card.
ProductScreen.do.clickDisplayedProduct('Gift Card');
TextInputPopup.check.isShown();
TextInputPopup.do.inputText('044123456');
TextInputPopup.do.clickConfirm();
PosLoyalty.check.orderTotalIs('5.00');
PosLoyalty.exec.finalizeOrder('Cash');
// Partially use the gift card. (4$)
ProductScreen.exec.addOrderline('Desk Pad', '2', '2', '4.0');
PosLoyalty.do.enterCode('044123456');
PosLoyalty.check.orderTotalIs('0.00');
PosLoyalty.exec.finalizeOrder('Cash');
// Use the remaining of the gift card. (5$ - 4$ = 1$)
ProductScreen.exec.addOrderline('Whiteboard Pen', '6', '6', '36.0');
PosLoyalty.do.enterCode('044123456');
PosLoyalty.check.orderTotalIs('35.00');
PosLoyalty.exec.finalizeOrder('Cash');
Tour.register('GiftCardProgramScanUseTour', { test: true, url: '/pos/web' }, getSteps());
//#endregion

startSteps();
ProductScreen.do.confirmOpeningPopup();
ProductScreen.do.clickHomeCategory();
ProductScreen.do.clickDisplayedProduct('Gift Card');
TextInputPopup.check.isShown();
TextInputPopup.do.inputText('044123456');
TextInputPopup.do.clickConfirm();
PosLoyalty.check.orderTotalIs('50.00');
PosLoyalty.exec.finalizeOrder('Cash');
ProductScreen.do.clickPartnerButton();
ProductScreen.do.clickCustomer("partner_a");
ProductScreen.exec.addOrderline("product_a", "1");
PosLoyalty.do.enterCode("044123456");
PosLoyalty.check.orderTotalIs("50.00");
PosLoyalty.check.pointsAwardedAre("100"),
PosLoyalty.exec.finalizeOrder("Cash", "50");
Tour.register("PosLoyaltyPointsGiftcard", { test: true, url: "/pos/web" }, getSteps());

startSteps();
ProductScreen.do.confirmOpeningPopup();
ProductScreen.do.clickHomeCategory();
ProductScreen.do.clickDisplayedProduct('Gift Card');
TextInputPopup.check.isShown();
TextInputPopup.do.inputText('044123456');
TextInputPopup.do.clickConfirm();
PosLoyalty.check.orderTotalIs('50.00');
PosLoyalty.exec.finalizeOrder('Cash');
ProductScreen.do.clickDisplayedProduct("Test Product A");
PosLoyalty.do.enterCode("044123456");
PosLoyalty.check.orderTotalIs("50.00");
ProductScreen.check.checkTaxAmount("-6.52");
Tour.register("PosLoyaltyGiftCardTaxes", { test: true }, getSteps());

startSteps();
ProductScreen.do.confirmOpeningPopup();
ProductScreen.do.clickHomeCategory();
ProductScreen.do.clickDisplayedProduct('Gift Card');
TextInputPopup.check.isShown();
TextInputPopup.do.inputText('044123456');
TextInputPopup.do.clickConfirm();
PosLoyalty.check.orderTotalIs('0.00');
ProductScreen.do.pressNumpad("Price 5");
PosLoyalty.check.orderTotalIs('5.00');
PosLoyalty.exec.finalizeOrder('Cash');
Tour.register("PosLoyaltyGiftCardNoPoints", { test: true }, getSteps());
