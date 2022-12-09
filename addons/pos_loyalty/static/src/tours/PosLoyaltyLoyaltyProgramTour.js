/** @odoo-module **/

import { PosLoyalty } from "@pos_loyalty/tours/PosLoyaltyTourMethods";
import { ProductScreen } from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import { getSteps, startSteps } from "@point_of_sale/../tests/tours/helpers/utils";
import Tour from "web_tour.tour";

startSteps();

ProductScreen.do.confirmOpeningPopup();
ProductScreen.do.clickHomeCategory();

// Order1: Generates 2 points.
ProductScreen.exec.addOrderline("Whiteboard Pen", "2");
ProductScreen.do.clickPartnerButton();
ProductScreen.do.clickCustomer("Test Partner AAA");
PosLoyalty.check.orderTotalIs("6.40");
PosLoyalty.exec.finalizeOrder("Cash", "10");

// Order2: Consumes points to get free product.
ProductScreen.do.clickPartnerButton();
ProductScreen.do.clickCustomer("Test Partner AAA");
ProductScreen.do.clickDisplayedProduct("Whiteboard Pen");
ProductScreen.check.selectedOrderlineHas("Whiteboard Pen", "1.00");
ProductScreen.do.clickDisplayedProduct("Whiteboard Pen");
ProductScreen.check.selectedOrderlineHas("Whiteboard Pen", "2.00");
// At this point, Test Partner AAA has 4 points.
PosLoyalty.check.isRewardButtonHighlighted(true);
ProductScreen.do.clickDisplayedProduct("Whiteboard Pen");
ProductScreen.check.selectedOrderlineHas("Whiteboard Pen", "3.00");
PosLoyalty.check.hasRewardLine("Free Product - Whiteboard Pen", "-3.20", "1.00");
PosLoyalty.check.isRewardButtonHighlighted(false);
PosLoyalty.check.orderTotalIs("6.40");
PosLoyalty.exec.finalizeOrder("Cash", "10");

// Order3: Generate 4 points.
// - Initially gets free product, but was removed automatically by changing the
//   number of items to zero.
// - It's impossible to checked here if the free product reward is really removed
//   so we check in the backend the number of orders that consumed the reward.
ProductScreen.exec.addOrderline("Whiteboard Pen", "4");
PosLoyalty.check.orderTotalIs("12.80");
ProductScreen.do.clickPartnerButton();
ProductScreen.do.clickCustomer("Test Partner AAA");
PosLoyalty.check.isRewardButtonHighlighted(true);
ProductScreen.do.clickDisplayedProduct("Whiteboard Pen");
PosLoyalty.check.hasRewardLine("Free Product - Whiteboard Pen", "-3.20", "1.00");
PosLoyalty.check.isRewardButtonHighlighted(false);
ProductScreen.do.pressNumpad("Backspace");
// At this point, the reward line should have been automatically removed
// because there is not enough points to purchase it. Unfortunately, we
// can't check that here.
PosLoyalty.check.orderTotalIs("0.00");
ProductScreen.do.clickDisplayedProduct("Whiteboard Pen");
ProductScreen.check.selectedOrderlineHas("Whiteboard Pen", "1.00");
ProductScreen.do.clickDisplayedProduct("Whiteboard Pen");
ProductScreen.check.selectedOrderlineHas("Whiteboard Pen", "2.00");
ProductScreen.do.clickDisplayedProduct("Whiteboard Pen");
ProductScreen.check.selectedOrderlineHas("Whiteboard Pen", "3.00");
ProductScreen.do.clickDisplayedProduct("Whiteboard Pen");
PosLoyalty.check.isRewardButtonHighlighted(false);
ProductScreen.check.selectedOrderlineHas("Whiteboard Pen", "4.00");
PosLoyalty.check.isRewardButtonHighlighted(true);

PosLoyalty.check.orderTotalIs("12.80");
PosLoyalty.exec.finalizeOrder("Cash", "20");

Tour.register("PosLoyaltyLoyaltyProgram1", { test: true, url: "/pos/web" }, getSteps());

startSteps();

ProductScreen.do.clickHomeCategory();

// Order1: Immediately set the customer to Test Partner AAA which has 4 points.
// - He has enough points to purchase a free product but since there is still
//   no product in the order, reward button should not yet be highlighted.
// - Furthermore, clicking the reward product should not add it as reward product.
ProductScreen.do.clickPartnerButton();
ProductScreen.do.clickCustomer("Test Partner AAA");
// No item in the order, so reward button is off.
PosLoyalty.check.isRewardButtonHighlighted(false);
ProductScreen.do.clickDisplayedProduct("Whiteboard Pen");
PosLoyalty.check.isRewardButtonHighlighted(true);
ProductScreen.do.clickDisplayedProduct("Whiteboard Pen");
PosLoyalty.check.hasRewardLine("Free Product - Whiteboard Pen", "-3.20", "1.00");
PosLoyalty.check.isRewardButtonHighlighted(false);
PosLoyalty.check.orderTotalIs("3.20");
PosLoyalty.exec.finalizeOrder("Cash", "10");

// Order2: Generate 4 points for Test Partner CCC.
// - Reference: Order2_CCC
// - But set Test Partner BBB first as the customer.
ProductScreen.do.clickPartnerButton();
ProductScreen.do.clickCustomer("Test Partner BBB");
PosLoyalty.check.isRewardButtonHighlighted(false);
ProductScreen.do.clickDisplayedProduct("Whiteboard Pen");
ProductScreen.check.selectedOrderlineHas("Whiteboard Pen", "1.00");
ProductScreen.do.clickDisplayedProduct("Whiteboard Pen");
ProductScreen.check.selectedOrderlineHas("Whiteboard Pen", "2.00");
ProductScreen.do.clickDisplayedProduct("Whiteboard Pen");
ProductScreen.check.selectedOrderlineHas("Whiteboard Pen", "3.00");
PosLoyalty.check.isRewardButtonHighlighted(false);
ProductScreen.do.clickDisplayedProduct("Whiteboard Pen");
ProductScreen.check.selectedOrderlineHas("Whiteboard Pen", "4.00");
PosLoyalty.check.isRewardButtonHighlighted(true);
ProductScreen.do.clickPartnerButton();
ProductScreen.do.clickCustomer("Test Partner CCC");
PosLoyalty.check.customerIs("Test Partner CCC");
PosLoyalty.check.orderTotalIs("12.80");
PosLoyalty.exec.finalizeOrder("Cash", "20");

// Order3: Generate 3 points for Test Partner BBB.
// - Reference: Order3_BBB
// - But set Test Partner CCC first as the customer.
ProductScreen.do.clickPartnerButton();
ProductScreen.do.clickCustomer("Test Partner CCC");
PosLoyalty.check.isRewardButtonHighlighted(false);
ProductScreen.exec.addOrderline("Whiteboard Pen", "3");
ProductScreen.do.clickPartnerButton();
ProductScreen.do.clickCustomer("Test Partner BBB");
PosLoyalty.check.customerIs("Test Partner BBB");
PosLoyalty.check.orderTotalIs("9.60");
PosLoyalty.exec.finalizeOrder("Cash", "10");

// Order4: Should not have reward because the customer will be removed.
// - Reference: Order4_no_reward
ProductScreen.do.clickDisplayedProduct("Whiteboard Pen");
ProductScreen.check.selectedOrderlineHas("Whiteboard Pen", "1.00");
PosLoyalty.check.isRewardButtonHighlighted(false);
ProductScreen.do.clickPartnerButton();
ProductScreen.do.clickCustomer("Test Partner CCC");
PosLoyalty.check.isRewardButtonHighlighted(true);
PosLoyalty.do.clickRewardButton();
PosLoyalty.check.hasRewardLine("Free Product - Whiteboard Pen", "-3.20", "1.00");
ProductScreen.do.clickPartnerButton();
// This deselects the customer.
PosLoyalty.do.unselectPartner();
PosLoyalty.check.customerIs("Customer");
PosLoyalty.check.orderTotalIs("3.20");
PosLoyalty.exec.finalizeOrder("Cash", "10");

Tour.register("PosLoyaltyLoyaltyProgram2", { test: true, url: "/pos/web" }, getSteps());
