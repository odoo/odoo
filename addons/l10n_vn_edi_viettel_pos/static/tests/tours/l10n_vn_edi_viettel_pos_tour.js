import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as TicketScreen from "@point_of_sale/../tests/tours/utils/ticket_screen_util";
import * as TextInputPopup from "@point_of_sale/../tests/tours/utils/text_input_popup_util";
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
            {
                content: "go to next screen from receipt",
                trigger: ".receipt-screen [name='done'].highlight",
                run: "click",
            },
            ...ProductScreen.clickRefund(),
            TicketScreen.selectFilter("Paid"),
            TicketScreen.selectOrder("-0001"),
            {
                content: "command name should be Print Tax Invoice",
                trigger: '.control-buttons button:contains("Print Tax Invoice")',
            },
            ProductScreen.clickNumpad("1"),
            TicketScreen.confirmRefund(),

            ProductScreen.clickPayButton(),
            PaymentScreen.isInvoiceButtonUnchecked(),
            PaymentScreen.clickInvoiceButton(),
            Dialog.is({ title: "Refund Reason" }),
            TextInputPopup.inputText("Customer return"),
            Dialog.confirm(),
            PaymentScreen.isInvoiceButtonChecked(),
        ].flat(),
});
