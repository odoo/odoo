import { patch } from '@web/core/utils/patch';

import { PaymentForm } from '@payment/interactions/payment_form';

patch(PaymentForm.prototype, {
    /**
     * Set whether we are paying an installment before submitting.
     *
     * @override method from payment.payment_form
     * @param {Event} ev
     * @returns {void}
     */
    async submitForm(ev) {
        ev.stopPropagation();
        ev.preventDefault();

        const paymentDialog = this.el.closest("#pay_with");
        const chosenPaymentDetails = paymentDialog
            ? paymentDialog.querySelector(".o_btn_payment_tab.active")
            : null;
        if (chosenPaymentDetails){
            if (chosenPaymentDetails.id === "o_payment_installments_tab") {
                this.paymentContext.amount = parseFloat(this.paymentContext.invoiceNextAmountToPay);
            } else {
                this.paymentContext.amount = parseFloat(this.paymentContext.invoiceAmountDue);
            }
        }
        await super.submitForm(...arguments);
    },

        /**
     * Prepare the params for the RPC to the transaction route.
     *
     * @override method from payment.payment_form
     * @private
     * @return {object} The transaction route params.
     */
        _prepareTransactionRouteParams() {
            const transactionRouteParams = super._prepareTransactionRouteParams(...arguments);
            transactionRouteParams.payment_reference = this.paymentContext.paymentReference;
            return transactionRouteParams;
        },
});
