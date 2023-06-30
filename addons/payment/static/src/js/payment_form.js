/** @odoo-module alias=payment.form **/

import publicWidget from 'web.public.widget';
import core from "../../../../web/static/src/legacy/js/services/core";

publicWidget.registry.PaymentForm = publicWidget.Widget.extend({
    selector: '#o_payment_form',
    events: Object.assign({}, publicWidget.Widget.prototype.events, {
        'click button[name="o_payment_submit_button"]': '_onClickSubmitButton',
    }),

    /**
     * @override
     */
    async start() {
        this.txContext = {}; // Synchronously initialize txContext before any await.
        Object.assign(this.txContext, this.el.dataset);
        await this._super(...arguments);
        this.$('[data-bs-toggle="tooltip"]').tooltip();
    },
    //
    // /**
    //  * TODO.
    //  *
    //  * @private
    //  * @param {Event} ev
    //  * @return {void}
    //  */
    // _onClickSubmitButton(ev) {
    //     ev.stopPropagation();
    //     ev.preventDefault();
    //
    //     const checkedRadio = this.el.querySelector('input[name="o_payment_radio"]:checked');
    //     const provider = this._getProviderFromRadio(checkedRadio);
    //     const paymentOptionId = this._getPaymentOptionIdFromRadio(checkedRadio);
    //     const paymentMethodId = this._getPaymentMethodIdFromRadio(checkedRadio);
    //     const operation = this._getOperationFromRadio(checkedRadio);
    //     this.txContext['tokenizationRequested'] = false;  // TODO
    //     this._processPayment(provider, paymentOptionId, paymentMethodId, operation);
    // },
    //
    // /**
    //  * Determine and return the code of the provider of the selected payment option.
    //  *
    //  * @private
    //  * @param {HTMLElement} radio - The radio button linked to the payment option.
    //  * @return {string} The code of the provider of the payment option linked to the radio button.
    //  */
    // _getProviderFromRadio(radio) {
    //     return radio.dataset['provider'];
    // },
    //
    // /**
    //  * Determine and return the id of the selected payment method.
    //  *
    //  * @private
    //  * @param {HTMLElement} radio - The radio button linked to the payment option.
    //  * @return {number} The id of the selected payment method.
    //  */
    // _getPaymentMethodIdFromRadio(radio) {
    //     return Number(radio.dataset['paymentMethodId']);
    // },
    //
    // /**
    //  * Determine and return the id of the selected payment option.
    //  *
    //  * @private
    //  * @param {HTMLElement} radio - The radio button linked to the payment option.
    //  * @return {number} The id of the payment option linked to the radio button.
    //  */
    // _getPaymentOptionIdFromRadio(radio) {
    //     return Number(radio.dataset['paymentOptionId']);
    // },
    //
    // /**
    //  * Determine and return the payment operation of the selected payment option.
    //  *
    //  * As some providers implement more than one payment operation, it cannot be inferred from the
    //  * radio button only. The latter indicates only whether the payment option is a token. If not,
    //  * the transaction context is looked up to determine the operation. TODO ANV double-check now that all operations are possible
    //  *
    //  * @private
    //  * @param {HTMLElement} radio - The radio button linked to the payment option.
    //  * @return {string} The operation of the selected payment option.
    //  */
    // _getOperationFromRadio(radio) {
    //     return 'online_redirect'; // TODO ANV hack for Stripe
    // },
    //
    // /**
    //  * Process the payment.
    //  *
    //  * For a provider to do pre-processing work on the transaction processing flow, or to define its
    //  * entire own flow that requires re-scheduling the RPC to the transaction route, it must
    //  * override this method. If only post-processing work is needed, an override of
    //  * `_processRedirectPayment`,`_processDirectPayment` or `_processTokenPayment` might be more
    //  * appropriate.
    //  *
    //  * @private
    //  * @param {string} code - The code of the payment option's provider.
    //  * @param {number} paymentOptionId - The id of the payment option handling the transaction.
    //  * @param {number} paymentMethod - The code of the selected payment method.
    //  * @param {string} operation - The payment operation of the transaction.
    //  * @return {void}
    //  */
    // _processPayment: function (code, paymentOptionId, paymentMethodId, operation) {
    //     // Query the server to create a transaction and retrieve the processing values.
    //     this._rpc({
    //         route: this.txContext['transactionRoute'],
    //         params: this._prepareTransactionRouteParams(
    //             code, paymentOptionId, paymentMethodId, operation
    //         ),
    //     }).then(processingValues => {
    //         if (operation === 'online_redirect') {
    //             this._processRedirectPayment(code, paymentOptionId, processingValues);
    //         } else if (operation === 'direct') {
    //             // TODO ANV
    //         } else if (operation === 'token') {
    //             // TODO ANV
    //         }
    //     }).guardedCatch(error => {
    //         error.event.preventDefault();
    //         // this._displayError(
    //         //     _t("Server Error"),
    //         //     _t("We are not able to process your payment."),
    //         //     error.message.data.message,
    //         // ); TODO ANV
    //     });
    // },
    //
    // /**
    //  * Prepare the params to send to the transaction route.
    //  *
    //  * For a provider to overwrite generic params or to add provider-specific ones, it must override
    //  * this method and return the extended transaction route params.
    //  *
    //  * @private
    //  * @param {string} code - The code of the selected payment option provider.
    //  * @param {number} paymentOptionId - The id of the selected payment option.
    //  * @param {string} paymentMethodId - The id of the selected payment method.
    //  * @param {string} operation - The payment operation of the selected payment option.
    //  * @return {object} The transaction route params.
    //  */
    // _prepareTransactionRouteParams: function (code, paymentOptionId, paymentMethodId, operation) {
    //     return {
    //         'payment_option_id': paymentOptionId,
    //         'payment_method_id': paymentMethodId,
    //         'reference_prefix': this.txContext['referencePrefix']?.toString() ?? null,
    //         'amount': this.txContext['amount'] !== undefined
    //             ? parseFloat(this.txContext['amount']) : null,
    //         'currency_id': this.txContext['currencyId']
    //             ? parseInt(this.txContext['currencyId']) : null,
    //         'partner_id': parseInt(this.txContext['partnerId']),
    //         // 'operation': operation,  // TODO ANV
    //         'flow': 'redirect', // TODO ANV
    //         'tokenization_requested': this.txContext['tokenizationRequested'],
    //         'landing_route': this.txContext['landingRoute'],
    //         'is_validation': this.txContext['isValidation'],
    //         'access_token': this.txContext['accessToken'],
    //         'csrf_token': core.csrf_token,
    //     };
    // },
    //
    // /**
    //  * Redirect the customer by submitting the redirect form included in the processing values.
    //  *
    //  * For a provider to redefine the processing of the payment with redirection flow, it must
    //  * override this method.
    //  *
    //  * @private
    //  * @param {string} code - The code of the provider.
    //  * @param {number} providerId - The id of the provider handling the transaction.
    //  * @param {object} processingValues - The processing values of the transaction.
    //  * @return {void}
    //  */
    // _processRedirectPayment(code, providerId, processingValues) {
    //     const template = document.createElement('template');
    //     template.innerHTML = processingValues['redirect_form_html'].trim();
    //     const redirectForm = template.content.firstChild;
    //     redirectForm.setAttribute('target', '_top'); // Ensure ext. redirections when in an iframe.
    //     this.el.appendChild(redirectForm);  // Insert the redirect form in the DOM.
    //     redirectForm.submit();  // Submit the form.
    // },

});

export default publicWidget.registry.PaymentForm;
