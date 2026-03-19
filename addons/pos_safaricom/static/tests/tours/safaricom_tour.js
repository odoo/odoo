import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import { registry } from "@web/core/registry";

// Test M-PESA Express payment flow
registry.category("web_tour.tours").add("MpesaExpressTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Desk Pad", "1", "10.0", "10.0"),
            ProductScreen.clickPayButton(),
            PaymentScreen.isShown(),
            PaymentScreen.clickPaymentMethod("M-PESA Express"),
            {
                content: "Enter phone number",
                trigger: ".form-control",
                run: "edit 254712345678",
            },
            Dialog.confirm(),
            PaymentScreen.isShown(),
        ].flat(),
});

// Test Lipa na M-PESA payment flow with QR code
registry.category("web_tour.tours").add("LipaNaMpesaTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Desk Pad", "1", "15.0", "15.0"),
            ProductScreen.clickPayButton(),
            PaymentScreen.isShown(),
            PaymentScreen.clickPaymentMethod("Lipa na M-PESA"),

            // Wait for transaction popup to show
            {
                content: "Transaction popup should be visible",
                trigger: ".modal-dialog",
            },

            // Click QR code button to display it
            {
                content: "Click QR code button to show QR code",
                trigger: ".modal-footer button.ms-auto",
                run: "click",
            },

            // Verify QR code is now visible
            {
                content: "QR code should be visible after clicking button",
                trigger: ".modal-dialog img[alt='M-Pesa QR Code']",
            },

            // Close the popup
            {
                content: "Click Cancel to close",
                trigger: ".modal-footer button.btn-secondary:not(.ms-auto)",
                run: "click",
            },

            // Verify payment line is in retry state and not successful
            {
                content: "Payment line should be in retry state",
                trigger: ".paymentlines .paymentline.selected.retry",
            },
            {
                content: "Payment should not be validated",
                trigger: ".payment-screen .button.pay:not(.highlight)",
            },
        ].flat(),
});
