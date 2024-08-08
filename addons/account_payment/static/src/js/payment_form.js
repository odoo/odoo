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
        if (chosenPaymentDetails && chosenPaymentDetails.id === "o_payment_installments_tab") {
            this.paymentContext.payNextInstallment = true;
        }
        await this._super(...arguments);
    },

    /**
     * Add installment specific params for the RPC to the transaction route.
     *
     * @override method from payment.payment_form
     * @private
     * @returns {Object} The transaction route params.
     */
    _prepareTransactionRouteParams() {
        const transactionRouteParams = this._super(...arguments);

        const amountCustom =
            this.paymentContext.amountCustom && parseFloat(this.paymentContext.amountCustom);
        const amountOverdue =
            this.paymentContext.amountOverdue && parseFloat(this.paymentContext.amountOverdue);
        const amountNextInstallment =
            this.paymentContext.amountNextInstallment &&
            parseFloat(this.paymentContext.amountNextInstallment);

        if (this.paymentContext.payNextInstallment) {
            transactionRouteParams.amount = amountCustom || amountOverdue || amountNextInstallment;
            if (!amountCustom && !amountOverdue) {
                transactionRouteParams.name_next_installment =
                    this.paymentContext.nameNextInstallment;
            }
        }

        return transactionRouteParams;
    },
});
