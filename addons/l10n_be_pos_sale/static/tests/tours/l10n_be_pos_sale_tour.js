/** @odoo-module */
import * as PaymentScreen from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";
import * as ProductScreenPos from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as ProductScreenSale from "@pos_sale/../tests/helpers/ProductScreenTourMethods";
import * as Dialog from "@point_of_sale/../tests/tours/helpers/DialogTourMethods";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/helpers/ReceiptScreenTourMethods";
import { negateStep } from "@point_of_sale/../tests/tours/helpers/utils";
const ProductScreen = { ...ProductScreenPos, ...ProductScreenSale };
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PosSettleOrderIsInvoice", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            Dialog.confirm("Open session"),
            ProductScreen.controlButton("Quotation/Order"),
            ProductScreen.selectNthOrder(2),
            ProductScreen.clickPayButton(),
            PaymentScreen.isInvoiceButtonChecked(),
            PaymentScreen.clickInvoiceButton(),
            Dialog.is({ title: "This order needs to be invoiced" }),
            Dialog.confirm(),
            PaymentScreen.isInvoiceButtonChecked(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            ReceiptScreen.clickNextOrder(),

            ProductScreen.controlButton("Quotation/Order"),
            ProductScreen.selectFirstOrder(),
            ProductScreen.clickPayButton(),
            negateStep(PaymentScreen.isInvoiceButtonChecked()),
            PaymentScreen.clickInvoiceButton(),
            PaymentScreen.isInvoiceButtonChecked(),
        ].flat(),
});

registry.category("web_tour.tours").add("PosSettleOrderTryInvoice", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            Dialog.confirm("Open session"),
            ProductScreen.controlButton("Quotation/Order"),
            ProductScreen.selectFirstOrder(),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickInvoiceButton(),
            PaymentScreen.isInvoiceButtonChecked(),
        ].flat(),
});
