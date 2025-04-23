import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("ReceiptWithHSNSummaryTour", {
    checkDelay: 50,
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Magnetic Board"),
            ProductScreen.clickDisplayedProduct("Monitor Stand"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            ReceiptScreen.receiptIsThere(),
            // First order line contains HSN Code
            {
                trigger: ".orderline:eq(0) .pos-receipt-left-padding span:contains('HSN Code:')",
            },
            // Second order line does not contain HSN Code
            {
                trigger:
                    ".orderline:eq(1):not(:has(.pos-receipt-left-padding span:contains('HSN Code:'))",
            },
            {
                trigger: "table.hsn-summary-table",
            },
        ].flat(),
});
