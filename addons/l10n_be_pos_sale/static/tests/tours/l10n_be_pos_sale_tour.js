/** @odoo-module */

import { ErrorPopup } from "@point_of_sale/../tests/tours/helpers/ErrorPopupTourMethods";
import { PaymentScreen } from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";
import { ProductScreen } from "@pos_sale/../tests/helpers/ProductScreenTourMethods";
import { getSteps, startSteps } from "@point_of_sale/../tests/tours/helpers/utils";
import { registry } from "@web/core/registry";

// signal to start generating steps
// when finished, steps can be taken from getSteps
startSteps();

ProductScreen.do.confirmOpeningPopup();
ProductScreen.do.clickQuotationButton();
ProductScreen.do.selectFirstOrder();
ProductScreen.do.clickPayButton();
PaymentScreen.check.isInvoiceButtonChecked();
PaymentScreen.do.clickInvoiceButton();
PaymentScreen.check.isInvoiceButtonChecked();
ErrorPopup.do.clickConfirm();

registry.category("web_tour.tours").add("PosSettleOrderIsInvoice", { test: true, url: "/pos/ui", steps: getSteps() });
