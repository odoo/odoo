import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
import * as TicketScreen from "@point_of_sale/../tests/pos/tours/utils/ticket_screen_util";
import * as TextInputPopup from "@point_of_sale/../tests/generic_helpers/text_input_popup_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("L10nVnEdiPosConfigErrorTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Small Shelf", "1"),
            ProductScreen.clickPayButton(),
            {
                content: "enable invoice option if needed",
                trigger: ".payment-buttons .js_invoice",
                run: () => {
                    const invoiceButton = document.querySelector(".payment-buttons .js_invoice");
                    if (!invoiceButton.classList.contains("highlight")) {
                        invoiceButton.click();
                    }
                },
            },
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            Dialog.is({ title: "Configuration Error" }),
            Dialog.bodyIs("Set a POS Symbol"),
            Dialog.confirm(),
        ].flat(),
});

registry.category("web_tour.tours").add("L10nVnEdiPosRefundReasonTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.addOrderline("Small Shelf", "1"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ...ReceiptScreen.clickNextOrder(),
            ...ProductScreen.clickRefund(),
            TicketScreen.selectFilter("Paid"),
            TicketScreen.selectOrder("001"),
            {
                content: "command name should be Print Tax Invoice",
                trigger: '.control-buttons button:contains("Print Tax Invoice")',
            },
            ProductScreen.clickNumpad("1"),
            TicketScreen.confirmRefund(),

            PaymentScreen.isInvoiceButtonUnchecked(),
            PaymentScreen.clickInvoiceButton(),
            Dialog.is({ title: "Refund Reason" }),
            TextInputPopup.inputText("Customer return"),
            Dialog.confirm(),
            PaymentScreen.isInvoiceButtonChecked(),
        ].flat(),
});
