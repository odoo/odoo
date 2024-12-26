/** @odoo-module **/

import PaymentForm from "@payment/js/payment_form";

PaymentForm.include({
    /**
     * Set whether we are paying an installment before submitting.
     *
     * @override method from payment.payment_form
     * @private
     * @param {Event} ev
     * @returns {void}
     */
    async _submitForm(ev) {
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
        await this._super(...arguments);
    },

        /**
     * Prepare the params for the RPC to the transaction route.
     *
     * @override method from payment.payment_form
     * @private
     * @return {object} The transaction route params.
     */
        _prepareTransactionRouteParams() {
            const transactionRouteParams =  this._super(...arguments);
            transactionRouteParams.payment_reference = this.paymentContext.paymentReference;
            return transactionRouteParams;
        },
});
