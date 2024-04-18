import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.PortalInvoicePayment = publicWidget.Widget.extend({
    selector: "#portal_invoice_payment",

    start: function () {
        const params = new URLSearchParams(window.location.search);
        const showPaymentModal = params.get("showPaymentModal") === "true";
        var button = document.getElementById("invoice_portal_pay_now_btn");
        // If the showPaymentModal parameter is set, click on the "Pay Now" button
        // Clicking on this button opens the payment modal
        if (showPaymentModal && button) {
            button.click();
        }
    },
});

export default publicWidget.registry.PortalInvoicePayment;
