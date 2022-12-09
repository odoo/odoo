/** @odoo-module */

import { ProductScreen } from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import { PaymentScreen } from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";
import { ReceiptScreen } from "@point_of_sale/../tests/tours/helpers/ReceiptScreenTourMethods";
import { getSteps, startSteps } from "@point_of_sale/../tests/tours/helpers/utils";
import Tour from "web_tour.tour";

startSteps();

ProductScreen.do.clickHomeCategory();

ProductScreen.do.clickDisplayedProduct("Zero Amount Product");
ProductScreen.check.selectedOrderlineHas("Zero Amount Product", "1.0", "1.0");
ProductScreen.do.pressNumpad("+/- 1");
ProductScreen.check.selectedOrderlineHas("Zero Amount Product", "-1.0", "-1.0");

ProductScreen.do.clickPayButton();
PaymentScreen.do.clickPaymentMethod("Bank");
PaymentScreen.check.remainingIs("0.00");
PaymentScreen.do.clickValidate();

ReceiptScreen.check.receiptIsThere();

Tour.register("FixedTaxNegativeQty", { test: true, url: "/pos/ui" }, getSteps());
