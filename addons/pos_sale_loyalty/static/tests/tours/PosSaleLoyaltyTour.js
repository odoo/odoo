/** @odoo-module **/

import * as PaymentScreen from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/helpers/ReceiptScreenTourMethods";
import * as ProductScreenPos from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as ProductScreenSale from "@pos_sale/../tests/helpers/ProductScreenTourMethods";
const ProductScreen = { ...ProductScreenPos, ...ProductScreenSale };
import { registry } from "@web/core/registry";

registry
    .category("web_tour.tours")
    .add('PosSaleLoyaltyTour1', {
        test: true,
        url: '/pos/ui',
        steps: () => [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickQuotationButton(),
            ProductScreen.selectFirstOrder(),
            ProductScreen.clickDisplayedProduct('Desk Pad'),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod('Bank'),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
        ].flat(),
    });

registry
    .category("web_tour.tours")
    .add('test_pos_sale_loyalty_ignored_in_pos', {
        test: true,
        steps: () => [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickQuotationButton(),
            ProductScreen.selectFirstOrder(),
            ProductScreen.totalAmountIs(90),
        ].flat(),
    });
