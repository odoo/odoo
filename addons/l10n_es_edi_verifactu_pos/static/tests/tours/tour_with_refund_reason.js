/** @odoo-module */

import * as ProductScreen from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/helpers/ReceiptScreenTourMethods";
import * as PaymentScreen from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";
import * as TicketScreen from "@point_of_sale/../tests/tours/helpers/TicketScreenTourMethods";
import * as Utils from "@point_of_sale/../tests/tours/helpers/utils";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("l10n_es_edi_verifactu_pos.tour_with_refund_reason", {
    test: true,
    steps: () => [
        ProductScreen.confirmOpeningPopup(),
        ProductScreen.clickHomeCategory(),
        // order
        ProductScreen.clickDisplayedProduct("verifactu_pos_product"),
        ProductScreen.clickPayButton(),
        PaymentScreen.clickPaymentMethod("Bank"),
        PaymentScreen.remainingIs("0.00"),
        PaymentScreen.clickValidate(),
        ReceiptScreen.isShown(),
        ReceiptScreen.clickNextOrder(),
        // refund
        ProductScreen.clickRefund(),
        TicketScreen.selectOrder("-0001"),
        ProductScreen.pressNumpad("1"),
        TicketScreen.toRefundTextContains("To Refund: 1.00"),
        TicketScreen.confirmRefund(),
        Utils.selectButton("R5:"),
        ProductScreen.isShown(),
        ProductScreen.clickPayButton(),
        PaymentScreen.clickPaymentMethod("Bank"),
        PaymentScreen.clickValidate(),
        ReceiptScreen.isShown(),
    ].flat(),
});

registry.category("web_tour.tours").add("l10n_es_edi_verifactu_pos.tour_invoiced_with_refund_reason", {
    test: true,
    steps: () => [
        ProductScreen.confirmOpeningPopup(),
        ProductScreen.clickHomeCategory(),
        // order
        ProductScreen.clickDisplayedProduct("verifactu_pos_product"),
        ProductScreen.clickPartnerButton(),
        ProductScreen.inputCustomerSearchbar("partner_b"),
        ProductScreen.clickCustomer("partner_b"),
        ProductScreen.clickPayButton(),
        PaymentScreen.clickInvoiceButton(),
        PaymentScreen.clickPaymentMethod("Bank"),
        PaymentScreen.remainingIs("0.00"),
        PaymentScreen.clickValidate(),
        ReceiptScreen.isShown(),
        ReceiptScreen.clickNextOrder(),
        // refund
        ProductScreen.clickRefund(),
        TicketScreen.selectOrder("-0001"),
        ProductScreen.pressNumpad("1"),
        TicketScreen.toRefundTextContains("To Refund: 1.00"),
        TicketScreen.confirmRefund(),
        Utils.selectButton("R4:"),
        // TicketBAI also adds a refund popup
        ...(registry.category("web_tour.tours").contains("spanish_pos_tbai_tour") ? [Utils.selectButton("R4:")] : []),
        ProductScreen.isShown(),
        ProductScreen.clickPayButton(),
        // The order should be marked as "To Invoice" already
        PaymentScreen.clickPaymentMethod("Bank"),
        PaymentScreen.clickValidate(),
        ReceiptScreen.isShown(),
    ].flat(),
});
