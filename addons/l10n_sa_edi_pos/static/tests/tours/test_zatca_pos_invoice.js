/* global posmodel */

import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("ZATCA_invoice_not_mandatory_if_settlement", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            {
                content: "Set the pos_settle_due to True and open payment screen",
                trigger: "body",
                run: () => {
                    posmodel.get_order().is_settling_account = true;
                    posmodel.showScreen("PaymentScreen", { orderUuid: posmodel.selectedOrderUuid });
                },
            },
            PaymentScreen.clickPartnerButton(),
            PaymentScreen.clickCustomer("AAA Partner"),
            PaymentScreen.isInvoiceButtonUnchecked(),
        ].flat(),
});

registry.category("web_tour.tours").add("ZATCA_invoice_mandatory_if_not_settlement", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            {
                content: "Set the pos_settle_due to False and open payment screen",
                trigger: "body",
                run: () => {
                    posmodel.get_order().is_settling_account = false;
                    posmodel.showScreen("PaymentScreen", { orderUuid: posmodel.selectedOrderUuid });
                },
            },
            PaymentScreen.clickPartnerButton(),
            PaymentScreen.clickCustomer("AAA Partner"),
            PaymentScreen.isInvoiceButtonChecked(),
            // Try to uncheck it and verify it remains checked
            PaymentScreen.clickInvoiceButton(),
            PaymentScreen.isInvoiceButtonChecked(),
        ].flat(),
});
