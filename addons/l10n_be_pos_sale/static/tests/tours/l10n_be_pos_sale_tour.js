/** @odoo-module */
import * as PaymentScreen from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";
import * as ProductScreenPos from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as ProductScreenSale from "@pos_sale/../tests/helpers/ProductScreenTourMethods";
import * as Dialog from "@point_of_sale/../tests/tours/helpers/DialogTourMethods";
const ProductScreen = { ...ProductScreenPos, ...ProductScreenSale };
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PosSettleOrderIsInvoice", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),
            ProductScreen.controlButton("Quotation/Order"),
            ProductScreen.selectFirstOrder(),
            ProductScreen.clickPayButton(),
            PaymentScreen.isInvoiceButtonChecked(),
            PaymentScreen.clickInvoiceButton(),
            Dialog.is({ title: "This order needs to be invoiced" }),
            Dialog.confirm(),
            PaymentScreen.isInvoiceButtonChecked(),
        ].flat(),
});
