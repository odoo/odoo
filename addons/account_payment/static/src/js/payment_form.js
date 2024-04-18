import PaymentForm from "@payment/js/payment_form";

PaymentForm.include({
    _prepareTransactionRouteParams() {
        return {
            ...this._super(...arguments),
            payment_reference: this.paymentContext["paymentReference"],
        };
    },
});
