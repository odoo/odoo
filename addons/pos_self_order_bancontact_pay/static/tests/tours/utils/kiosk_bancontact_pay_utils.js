export const followInstructionsTerminalStep = () => ({
    content: "Check that the payment page shows the terminal instructions container",
    trigger: ".payment-state-container h1:contains('Follow instructions on the terminal')",
});
export const scanQrCodeStep = () => ({
    content: "Check that the payment page shows the QR code to pay",
    trigger: ".payment-state-container .o_bancontact_frame",
});
export const processingPaymentStep = () => ({
    content: "Check that the payment page shows the processing payment message",
    trigger: ".payment-state-container h1:contains('Processing your payment...')",
});
export function notifiedDanger(message) {
    return {
        content: "close the notification",
        trigger: `.o_notification:has(.o_notification_bar.bg-danger):has(.o_notification_content:contains('${message}')) .o_notification_close`,
        run: "click",
    };
}
export function bancontactDialogError() {
    return [
        {
            content: "Check that the Bancontact Pay dialog shows an error message",
            trigger: ".o_dialog .modal-title:contains('Bancontact Payment Error')",
        },
        {
            content: "Close the Bancontact Pay dialog",
            trigger: ".o_dialog .modal-footer .btn:contains('Ok')",
            run: "click",
        },
    ];
}
