/** @odoo-module **/

// TODO sort
import publicWidget from '@web/legacy/js/public/public_widget';
import Dialog from '@web/legacy/js/core/dialog';
import { escape, sprintf } from '@web/core/utils/strings';
import core from '@web/legacy/js/services/core';
const _t = core._t;  // TODO see if better way to import now

publicWidget.registry.PaymentForm = publicWidget.Widget.extend({
    selector: '#o_payment_form',
    events: Object.assign({}, publicWidget.Widget.prototype.events, {
        'click [name="o_payment_radio"]': '_selectPaymentOption',
        'click [name="o_payment_submit_button"]': '_submitForm',
    }),

    // #=== WIDGET LIFECYCLE ===#

    /**
     * @override
     */
    async start() {
        // Synchronously initialize txContext before any await.
        this.txContext = {};
        Object.assign(this.txContext, this.el.dataset);

        await this._super(...arguments);

        // Expand the payment form of the selected payment option if there is only one.
        const checkedRadio = document.querySelector('input[name="o_payment_radio"]:checked');
        if (checkedRadio) {
            await this._expandInlineForm(checkedRadio);
            this._enableButton();
        } else {
            this._setPaymentFlow(); // Initialize the payment flow to let providers overwrite it.
        }

        this.$('[data-bs-toggle="tooltip"]').tooltip();
    },

    // #=== EVENT HANDLERS ===#

    /**
     * Open the inline form of the selected payment option, if any.
     *
     * @private
     * @param {Event} ev
     * @return {void}
     */
    async _selectPaymentOption(ev) {
        // Show the inputs in case they have been hidden.
        this._showInputs();

        // Disable the submit button while preparing the inline form.
        this._disableButton();

        // Unfold and prepare the inline form of the selected payment option.
        const checkedRadio = ev.target;
        await this._expandInlineForm(checkedRadio);

        // Re-enable the submit button after the inline form has been prepared.
        this._enableButton();
    },

    /**
     * Delegate the handling of the payment request to `_onClickPay`. TODO
     *
     * @private
     * @param {Event} ev
     * @return {void}
     */
    async _submitForm(ev) {
        ev.stopPropagation();
        ev.preventDefault();

        const checkedRadio = this.el.querySelector('input[name="o_payment_radio"]:checked');

        // TODO comment
        // this._hideError(); // Don't keep the error displayed if the user is going through 3DS2 TODO problably useless now that we use a dialog
        this._disableButton(true); // Block the entire UI to prevent fiddling with other widgets.

        // Process the payment flow of the selected payment option.
        const flow = this.txContext.flow = this._getPaymentFlow(checkedRadio);
        if (flow === 'token' && this.txContext['assignTokenRoute']) { // Token assignation flow. TODO consider implementing this flow only in subscriptions
            await this._assignToken(paymentOptionId); // TODO implement
        } else { // Both tokens and payment methods must process a payment operation.
            const providerCode = this.txContext.providerCode = this._getProviderCode(checkedRadio);
            const paymentOptionId = this.txContext.paymentOptionId = this._getPaymentOptionId(
                checkedRadio
            );
            const paymentMethodCode = this.txContext.paymentMethodCode = this._getPaymentMethodCode(
                checkedRadio
            );
            this.txContext.providerId = this._getProviderId(checkedRadio);
            if (this._getPaymentOptionType(checkedRadio) === 'token') {
                this.txContext.tokenId = paymentOptionId;
            } else { // 'payment_method'
                this.txContext.paymentMethodId = paymentOptionId;
            }
            this.txContext.tokenizationRequested = this._getInlineForm(checkedRadio)?.querySelector(
                '[name="o_payment_tokenize_checkbox"]'
            )?.checked ?? false;
            await this._initiatePaymentFlow(providerCode, paymentOptionId, paymentMethodCode, flow);
        }
    },

    // #=== DOM MANIPULATION ===#

    /**
     * Check if the submit button can be enabled and do it if so.
     *
     * The UI is also unblocked in case it had been blocked.
     *
     * @private
     * @return {void}
     */
    _enableButton() {
        if (this._canSubmit()) {
            this._getSubmitButton().removeAttribute('disabled');
        }
        $('body').unblock();
    },

    /**
     * Disable the submit button.
     *
     * @private
     * @param {boolean} blockUI - Whether the UI should also be blocked.
     * @return {void}
     */
    _disableButton(blockUI = false) {
        this._getSubmitButton().setAttribute('disabled', true);
        if (blockUI) { // TODO not sure it can be done here; see https://github.com/odoo/odoo/pull/81661
            $('body').block({
                message: false,
                overlayCSS: { backgroundColor: "#000", opacity: 0, zIndex: 1050 },
            });
        }
    },

    /**
     * Show the tokenization checkbox, its label, and the submit button.
     *
     * @private
     * @return {void}
     */
    _showInputs() {
        // Show the tokenization checkbox and its label.
        const tokenizeContainer = this.el.querySelector('[name="o_payment_tokenize_container"]');
        tokenizeContainer.classList.remove('d-none');

        // Show the submit button.
        this._getSubmitButton().classList.remove('d-none');
    },

    /**
     * Hide the tokenization checkbox, its label, and the submit button.
     *
     * The inputs should typically be hidden when the customer has to perform additional actions in
     * the inline form. All inputs are automatically shown again when the customer selects another
     * payment option.
     *
     * @private
     * @return {void}
     */
    _hideInputs() {
        // Hide the tokenization checkbox and its label.
        const tokenizeContainer = this.el.querySelector('[name="o_payment_tokenize_container"]');
        tokenizeContainer.classList.add('d-none');

        // Hide the submit button.
        this._getSubmitButton().classList.add('d-none');
    },

    /**
     * Open the inline form of the selected payment option and collapse the others.
     *
     * @private
     * @param {HTMLInputElement} radio - The radio button linked to the payment option.
     * @return {void}
     */
    async _expandInlineForm(radio) {
        this._collapseInlineForms(); // Collapse previously opened inline forms.
        this._hideErrorDialog(); // The error is no longer relevant if hidden with its inline form.
        this._setPaymentFlow(); // Reset the payment flow to let providers overwrite it.

        // Prepare the inline form of the selected payment option.
        const providerCode = this._getProviderCode(radio);
        const paymentProviderId = this._getProviderId(radio);
        const paymentOptionId = this._getPaymentOptionId(radio);
        const paymentMethodCode = this._getPaymentMethodCode(radio);
        const flow = this._getPaymentFlow(radio);
        await this._prepareInlineForm(
            providerCode, paymentProviderId, paymentOptionId, paymentMethodCode, flow
        );

        // Display the prepared inline form if it is not empty.
        const inlineForm = this._getInlineForm(radio);
        if (inlineForm && inlineForm.children.length > 0) {
            inlineForm.classList.remove('d-none');
        }
    },

    /**
     * Prepare the provider-specific inline form of the selected payment option.
     *
     * For a provider to manage an inline form, it must override this method and render the content
     * of the form.
     *
     * @private
     * @param {string} providerCode - The code of the selected payment option's provider.
     * @param {number} paymentProviderId; - The id of the provider.
     * @param {number} paymentOptionId - The id of the selected payment option.
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {string} flow - The payment flow of the selected payment option.
     * @return {void}
     */
    async _prepareInlineForm(
        providerCode, paymentProviderId, paymentOptionId, paymentMethodCode, flow
    ) {},

    /**
     * Collapse all inline forms of the current widget.
     *
     * @private
     * @return {void}
     */
    _collapseInlineForms() {
        this.el.querySelectorAll('[name="o_payment_inline_form"]').forEach(inlineForm => {
            inlineForm.classList.add('d-none');
        });
    },

    /**
     * Display an error dialog.
     *
     * @private
     * @param {string} title - The title of the error.
     * @param {string} description - The description of the error.
     * @param {string} error - The raw error message.
     * @return {Dialog} The error dialog.
     */
    _displayErrorDialog(title, description = '', error = '') {
        const checkedRadios = this.$('input[name="o_payment_radio"]:checked');
        this._enableButton();
        return new Dialog(null, {
            title: sprintf(_t("Error: %s"), title),
            size: 'medium',
            $content: `<p>${escape(description) || ''}</p><p>${escape(error) || ''}</p>`, // TODO format
            buttons: [{ text: _t("Ok"), close: true }]
        }).open();
    },

    /**
     * Hide the error dialog. TODO check if still needed if we also show the error as a dialog
     *
     * @private
     * @return {void}
     */
    _hideErrorDialog() {
        this.el.querySelector('[name="o_payment_error_dialog"]')?.remove();
    },

    // #=== PAYMENT FLOW ===#

    /**
     * Check whether the payment form can be submitted, i.e. whether exactly one payment option is
     * selected.
     *
     * For a module to add a condition on the submission of the form, it must override this method
     * and return whether both this method's condition and the override method's condition are met.
     *
     * @private
     * @return {boolean} Whether the form can be submitted.
     */
    _canSubmit() {
        return this.el.querySelectorAll('input[name="o_payment_radio"]:checked').length === 1;
    },

    /**
     * Set the payment flow for the selected payment option.
     *
     * For a provider to manage direct payments, it must call this method and set the payment flow
     * when its payment option is selected.
     *
     * @private
     * @param {string} flow - The flow for the selected payment option. Either 'redirect', 'direct',
     *                        or 'token'
     * @return {void}
     */
    _setPaymentFlow(flow = 'redirect') {
        if (['redirect', 'direct', 'token'].includes(flow)) {
            this.txContext.flow = flow;
        } else {
            console.warn(`The value ${flow} is not a supported flow. Falling back to redirect.`);
            this.txContext.flow = 'redirect';
        }
    },

    /**
     * Process the payment flow of the selected payment option.
     *
     * For a provider to do pre-processing work, or to process the payment flow in its own terms
     * (e.g., re-scheduling the RPC to the transaction route), it must override this method.
     *
     * To alter the flow-specific processing, it is advised to override `_processRedirectFlow`,
     * `_processDirectFlow`, or `_processTokenFlow` instead.
     *
     * @private
     * @param {string} providerCode - The code of the selected payment option's provider.
     * @param {number} paymentOptionId - The id of the selected payment option.
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {string} flow - The payment flow of the selected payment option.
     * @return {void}
     */
    async _initiatePaymentFlow(providerCode, paymentOptionId, paymentMethodCode, flow) {
        // Create a transaction and retrieve its processing values.
        this._rpc({
            route: this.txContext['transactionRoute'],
            params: this._prepareTransactionRouteParams(),
        }).then(processingValues => {
            if (flow === 'redirect') {
                this._processRedirectFlow(
                    providerCode, paymentOptionId, paymentMethodCode, processingValues
                );
            } else if (flow === 'direct') {
                this._processDirectFlow(
                    providerCode, paymentOptionId, paymentMethodCode, processingValues
                );
            } else if (flow === 'token') {
                this._processTokenFlow(
                    providerCode, paymentOptionId, paymentMethodCode, processingValues
                );
            }
        }).guardedCatch(error => {
            error.event.preventDefault();
            this._displayErrorDialog(
                _t("Server Error"),
                _t("We are not able to process your payment."),
                error.message.data.message,
            );
            this._enableButton(); // The button has been disabled before initiating the flow.
        });
    },

    /**
     * Prepare the params for the RPC to the transaction route.
     *
     * @private
     * @return {object} The transaction route params.
     */
    _prepareTransactionRouteParams() { // TODO rename
        return {
            'provider_id': this.txContext.providerId,
            'payment_method_id': this.txContext.paymentMethodId ?? null,
            'token_id': this.txContext.tokenId ?? null,
            'reference_prefix': this.txContext['referencePrefix']?.toString() ?? null,
            'amount': this.txContext['amount'] !== undefined
                ? parseFloat(this.txContext['amount']) : null,
            'currency_id': this.txContext['currencyId']
                ? parseInt(this.txContext['currencyId']) : null,
            'partner_id': parseInt(this.txContext['partnerId']),
            'flow': this.txContext['flow'],
            'tokenization_requested': this.txContext['tokenizationRequested'],
            'landing_route': this.txContext['landingRoute'],
            'is_validation': this.txContext['isValidation'],
            'access_token': this.txContext['accessToken'],
            'csrf_token': core.csrf_token,
        };
    },

    /**
     * Redirect the customer by submitting the redirect form included in the processing values.
     *
     * @private
     * @param {string} providerCode - The code of the selected payment option's provider.
     * @param {number} paymentOptionId - The id of the selected payment option.
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {object} processingValues - The processing values of the transaction.
     * @return {void}
     */
    _processRedirectFlow(providerCode, paymentOptionId, paymentMethodCode, processingValues) { // TODO check if works
        const redirectForm = processingValues['redirect_form_html'];
        redirectForm.setAttribute('id', 'o_payment_redirect_form');
        redirectForm.setAttribute('target', '_top');  // Ensures redirections when in an iframe.
        this.el.appendChild(redirectForm);
        redirectForm.submit();
    },

   /**
     * Process the provider-specific implementation of the direct payment flow.
     *
     * @private
     * @param {string} providerCode - The code of the selected payment option's provider.
     * @param {number} paymentOptionId - The id of the selected payment option.
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {object} processingValues - The processing values of the transaction.
     * @return {void}
     */
    _processDirectFlow(providerCode, paymentOptionId, paymentMethodCode, processingValues) {},

    /**
     * Redirect the customer to the status route.
     *
     * @private
     * @param {string} providerCode - The code of the selected payment option's provider.
     * @param {number} paymentOptionId - The id of the selected payment option.
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {object} processingValues - The processing values of the transaction.
     * @return {void}
     */
    _processTokenFlow(providerCode, paymentOptionId, paymentMethodCode, processingValues) {
        // The flow is already completed as payments by tokens are immediately processed.
        window.location = '/payment/status';
    },

    // #=== GETTERS ===#

    /**
     * Determine and return the inline form of the selected payment option.
     *
     * @private
     * @param {HTMLInputElement} radio - The radio button linked to the payment option.
     * @return {Element | null} The inline form of the selected payment option, if any.
     */
    _getInlineForm(radio) {
        const inlineFormContainer = radio.closest('[name="o_payment_option"]');
        return inlineFormContainer?.querySelector('[name="o_payment_inline_form"]');
    },

    /**
     * Find and return the submit button.
     *
     * The button is searched in the whole document, rather than only in the current form, to allow
     * modules to place it outside the payment form (e.g., eCommerce).
     *
     * @private
     * @return {Element} The submit button.
     */
    _getSubmitButton() {
        return document.querySelector('[name="o_payment_submit_button"]');
    },

    /**
     * Determine and return the payment flow of the selected payment option.
     *
     * As some providers implement both direct payments and the payment with redirection flow, we
     * cannot infer it from the radio button only. The radio button indicates only whether the
     * payment option is a token. If not, the transaction context is looked up to determine whether
     * the flow is 'direct' or 'redirect'.
     *
     * @private
     * @param {HTMLInputElement} radio - The radio button linked to the payment option.
     * @return {string} The flow of the selected payment option: 'redirect', 'direct' or 'token'.
     */
    _getPaymentFlow(radio) {
        if (this._getPaymentOptionType(radio) === 'token' || this.txContext.flow === 'token') { // TODO when is the operation overriding the select option?
            return 'token';
        } else if (this.txContext.flow === 'redirect') {
            return 'redirect';
        } else {
            return 'direct';
        }
    },

    /**
     * Determine and return the code of the selected payment method.
     *
     * @private
     * @param {HTMLElement} radio - The radio button linked to the payment method.
     * @return {string} The code of the selected payment method.
     */
    _getPaymentMethodCode(radio) {
        return radio.dataset['paymentMethodCode'];
    },

    /**
     * Determine and return the id of the selected payment option.
     *
     * @private
     * @param {HTMLElement} radio - The radio button linked to the payment option.
     * @return {number} The id of the selected payment option.
     */
    _getPaymentOptionId(radio) {
        return Number(radio.dataset['paymentOptionId']);
    },

    /**
     * Determine and return the type of the selected payment option.
     *
     * @private
     * @param {HTMLElement} radio - The radio button linked to the payment option.
     * @return {string} The type of the selected payment option: 'token' or 'payment_method'.
     */
    _getPaymentOptionType(radio) {
        return radio.dataset['paymentOptionType'];
    },

    /**
     * Determine and return the code of the provider of the selected payment option.
     *
     * @private
     * @param {HTMLElement} radio - The radio button linked to the payment option.
     * @return {string} The code of the provider of the selected payment option.
     */
    _getProviderCode(radio) {
        return radio.dataset['providerCode'];
    },

    /**
     * Determine and return the id of the provider of the selected payment option.
     *
     * @private
     * @param {HTMLElement} radio - The radio button linked to the payment option.
     * @return {number} The id of the provider of the selected payment option.
     */
    _getProviderId(radio) {
        return Number(radio.dataset['providerId']);
    },

    //
    // /**
    //  * TODO.
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
    //
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
