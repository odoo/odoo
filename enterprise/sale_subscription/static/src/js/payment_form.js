/** @odoo-module **/

import { ConfirmationDialog } from '@web/core/confirmation_dialog/confirmation_dialog';
import { _t } from '@web/core/l10n/translation';
import { renderToMarkup } from '@web/core/utils/render';

import paymentForm from '@payment/js/payment_form';

paymentForm.include({
    events: Object.assign({}, paymentForm.prototype.events || {}, {
        'change input[name="o_payment_automate_payments_new_token"]':
            "_onChangeAutomatePaymentsCheckbox",
    }),

    /**
     * Replace the base token deletion confirmation dialog to prevent token deletion if a linked
     * subscription is active.
     *
     * @override method from @payment/js/payment_form
     * @private
     * @param {number} tokenId - The id of the token whose deletion was requested.
     * @param {object} linkedRecordsInfo - The data relative to the documents linked to the token.
     * @return {void}
     */
    _challengeTokenDeletion(tokenId, linkedRecordsInfo) {
        if (linkedRecordsInfo.every(linkedRecordInfo => !linkedRecordInfo['active_subscription'])) {
            this._super(...arguments);
            return;
        }

        const body = renderToMarkup('sale_subscription.deleteTokenDialog', { linkedRecordsInfo });
        this.call('dialog', 'add', ConfirmationDialog, {
            title: _t("Warning!"),
            body,
            cancel: () => {},
        });
    },

    /**
     * Override of payment method to update the paymentContext.transactionRoute depending
     * on the order we are paying.
     * For subscription invoices, when the customer wants to save the token on the order,
     * we update the transaction route on the fly.
     *
     * @private
     * @param {Event} ev
     * @return {void}
     */
    async _submitForm(ev) {
        const checkedRadio = this.el.querySelector('input[name="o_payment_radio"]:checked');
        const inlineForm = this._getInlineForm(checkedRadio);

        // Fetch the `autoPaymentCheckboxNewToken` of the current payment method.
        const autoPaymentCheckboxNewToken = inlineForm?.querySelector(
            'input[name="o_payment_automate_payments_new_token"]'
        );
        // Fetch the `autoPaymentCheckboxSavedToken` of the current token.
        const autoPaymentCheckboxSavedToken = inlineForm?.querySelector(
            `input[name="o_payment_automate_payments_saved_token"]`
        );

        if ((autoPaymentCheckboxNewToken?.checked || autoPaymentCheckboxSavedToken?.checked) &&
            this.paymentContext.txRouteSubscription) {
            // TODO Should be replaced with an override of the account_payment controller to extend
            // it with subscription logic.
            this.paymentContext.transactionRoute = this.paymentContext.txRouteSubscription;
        }
        return this._super(...arguments);
    },

    /**
     * Automatically check `Save my payment details` checkbox after clicking in the `Automate payments` option.
     *
     * @private
     * @return {void}
     */
    _onChangeAutomatePaymentsCheckbox: function (ev) {
        // Fetch the `savePaymentMethodCheckbox` of the current payment method.
        const tokenizeContainer = ev.currentTarget.closest(
            'div[name="o_payment_tokenize_container"]'
        );
        const savePaymentMethodCheckbox = tokenizeContainer.querySelector(
            'input[name="o_payment_tokenize_checkbox"]'
        );
        savePaymentMethodCheckbox.checked = ev.currentTarget.checked;
        savePaymentMethodCheckbox.disabled = ev.currentTarget.checked;
        // Dispatch a fake event to update the payment form dependencies.
        savePaymentMethodCheckbox.dispatchEvent(new Event('input'));
    },

    /**
     * Prepare the params for the RPC to the transaction route.
     *
     * @private
     * @param {number} providerId - The id of the provider handling the transaction.
     * @returns {object} - The transaction route params.
     */
    _prepareTransactionRouteParams(providerId) {
        const transactionRouteParams = this._super(...arguments);
        if (this.paymentContext.subscriptionAnticipate) {
            transactionRouteParams['subscription_anticipate'] = this.paymentContext.subscriptionAnticipate;
        }
        return transactionRouteParams;
    },

});
