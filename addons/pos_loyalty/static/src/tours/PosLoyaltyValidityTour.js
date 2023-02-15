/** @odoo-module **/

import { PosLoyalty } from "@pos_loyalty/tours/PosLoyaltyTourMethods";
import { ProductScreen } from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import { getSteps, startSteps } from "@point_of_sale/../tests/tours/helpers/utils";
import { registry } from "@web/core/registry";

// First tour should not get any automatic rewards
startSteps();

ProductScreen.do.confirmOpeningPopup();
ProductScreen.do.clickHomeCategory();

// Not valid -> date
ProductScreen.exec.addOrderline("Whiteboard Pen", "5");
PosLoyalty.check.checkNoClaimableRewards();
PosLoyalty.exec.finalizeOrder("Cash", "20");

registry.category("web_tour.tours").add("PosLoyaltyValidity1", { test: true, url: "/pos/web", steps: getSteps() });

// Second tour
startSteps();

ProductScreen.do.clickHomeCategory();

// Valid
ProductScreen.exec.addOrderline("Whiteboard Pen", "5");
PosLoyalty.check.hasRewardLine("90% on the cheapest product", "-2.88");
PosLoyalty.exec.finalizeOrder("Cash", "20");

// Not valid -> usage
ProductScreen.exec.addOrderline("Whiteboard Pen", "5");
PosLoyalty.check.checkNoClaimableRewards();
PosLoyalty.exec.finalizeOrder("Cash", "20");

registry.category("web_tour.tours").add("PosLoyaltyValidity2", { test: true, url: "/pos/web", steps: getSteps() });
