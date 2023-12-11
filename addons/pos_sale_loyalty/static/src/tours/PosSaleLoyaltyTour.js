/** @odoo-module **/

import { PaymentScreen } from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";
import { ProductScreen } from "@pos_sale/../tests/helpers/ProductScreenTourMethods";
import { ReceiptScreen } from "@pos_sale/../tests/helpers/ReceiptScreenTourMethods";
import { getSteps, startSteps } from "@point_of_sale/../tests/tours/helpers/utils";
import { registry } from "@web/core/registry";

registry
    .category("web_tour.tours")
    .add('PosSaleLoyaltyTour1', {
        test: true,
        url: '/pos/ui',
        steps: () => {
            startSteps();

            ProductScreen.do.confirmOpeningPopup();
            ProductScreen.do.clickQuotationButton();
            ProductScreen.do.selectFirstOrder();
            ProductScreen.do.clickDisplayedProduct('Desk Pad');
            ProductScreen.do.clickPayButton();
            PaymentScreen.do.clickPaymentMethod('Bank');
            PaymentScreen.do.clickValidate();
            ReceiptScreen.check.isShown();

            return getSteps();
        }
    });
