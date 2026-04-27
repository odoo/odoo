/* global posmodel */

import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/utils/receipt_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as ProductScreenPos from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as ProductScreenResto from "@pos_restaurant/../tests/tours/utils/product_screen_util";
const ProductScreen = { ...ProductScreenPos, ...ProductScreenResto };
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as FloorScreen from "@pos_restaurant/../tests/tours/utils/floor_screen_util";
import * as Order from "@point_of_sale/../tests/tours/utils/generic_components/order_widget_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("FiskalyTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AA Test Partner"),
            // Customer without street name or a zip code is not allowed
            Dialog.confirm(),
            ProductScreen.clickCustomer("A powerful PoS man!"),
            ProductScreen.addOrderline("Coca-Cola", "1", "3"),
            ProductScreen.clickOrderButton(),
            Chrome.waitRequest(),
            ProductScreen.orderlinesHaveNoChange(),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("5"),
            Order.hasLine({
                productName: "Coca-Cola",
            }),
            ProductScreen.addOrderline("Coca-Cola", "1", "5"),
            ProductScreen.clickOrderButton(),
            Chrome.waitRequest(),
            ProductScreen.orderlinesHaveNoChange(),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickInvoiceButton(),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            {
                trigger: ".tss-info:contains('TSE-Transaktion')",
            },
            ReceiptScreen.clickNextOrder(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_fiskaly_tss_payload", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.addOrderline("Coca-Cola", "1", "5"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Random Name"),
            {
                content: "Check if the payload is correct",
                trigger: "body",
                run: () => {
                    const payment = posmodel.get_order()._createAmountPerPaymentTypeArray();
                    if (payment[0].payment_type != "CASH") {
                        throw new Error("Payment type should be CASH");
                    }
                },
            },
        ].flat(),
});

registry.category("web_tour.tours").add("test_fiskaly_receipt_printer", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.addOrderline("Coca-Cola", "1", "3"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ProductScreen.isShown(),
            Dialog.is({ title: "Connection to the printer failed" }),
            Dialog.cancel(),
        ].flat(),
});
