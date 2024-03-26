/** @odoo-module */
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as ProductScreenPos from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as ProductScreenSale from "@pos_sale/../tests/tours/utils/product_screen_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
const ProductScreen = { ...ProductScreenPos, ...ProductScreenSale };
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PosSettleOrderIsInvoice", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),
            ProductScreen.clickControlButton("Quotation/Order"),
            ProductScreen.selectFirstOrder(),
            ProductScreen.clickPayButton(),
            PaymentScreen.isInvoiceButtonChecked(),
            PaymentScreen.clickInvoiceButton(),
            Dialog.is({ title: "This order needs to be invoiced" }),
            Dialog.confirm(),
            PaymentScreen.isInvoiceButtonChecked(),
        ].flat(),
});
