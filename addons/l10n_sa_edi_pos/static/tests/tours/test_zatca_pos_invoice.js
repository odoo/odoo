/* global posmodel */

import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("ZATCA_invoice_not_mandatory_if_deposit", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            {
                content: "Set the pos_settle_due to True and open payment screen",
                trigger: "body",
                run: () => {
                    posmodel.selectedOrder.is_settling_account = true;
                    posmodel.navigate("PaymentScreen", { orderUuid: posmodel.selectedOrderUuid });
                },
            },
            PaymentScreen.clickPartnerButton(),
            PaymentScreen.clickCustomer("AAA Partner"),
            PaymentScreen.isInvoiceButtonUnchecked(),
        ].flat(),
});

registry.category("web_tour.tours").add("ZATCA_invoice_mandatory_if_regular_order", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            {
                content: "Set the pos_settle_due to False and open payment screen.",
                trigger: "body",
                run: () => {
                    posmodel.selectedOrder.is_settling_account = false;
                    posmodel.navigate("PaymentScreen", { orderUuid: posmodel.selectedOrderUuid });
                },
            },
            PaymentScreen.clickPartnerButton(),
            PaymentScreen.clickCustomer("AAA Partner"),
            PaymentScreen.isInvoiceButtonChecked(),
            // Try to uncheck it and verify it remains checked
            PaymentScreen.clickInvoiceButton(),
        ].flat(),
});
<<<<<<< d8942f5037f77c51c10f4182fff436ed1bb5de30
||||||| 8aeeada82f3e23f56e716906caf58969b4fb067d

registry.category("web_tour.tours").add("ZATCA_blocks_settle_due_and_sale_on_same_order", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            PartnerList.settleCustomerAccount(
                "AAAA Generic Partner",
                "23.0",
                "TSJ/2026/",
                "",
                false,
                false
            ),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            Dialog.is({ title: "Settlement Error" }),
        ].flat(),
});
=======

registry.category("web_tour.tours").add("ZATCA_blocks_settle_due_and_sale_on_same_order", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            PartnerList.settleCustomerAccount("AAAA Generic Partner", "23.0", "TSJ/"),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            Dialog.is({ title: "Settlement Error" }),
        ].flat(),
});
>>>>>>> 70a8b1a1a4a098f7241915f95a09a06122681acb
