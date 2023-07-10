/** @odoo-module **/

// TODO sort
import publicWidget from 'web.public.widget';
import Dialog from '@web/legacy/js/core/dialog';
import { escape, sprintf } from '@web/core/utils/strings';
import framework from 'web.framework';
import core from "../../../../web/static/src/legacy/js/services/core";

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

        // Extract contextual values from the radio button.
        const flow = this._getPaymentFlow(checkedRadio);
        const paymentOptionId = this._getPaymentOptionId(checkedRadio);
        const providerCode = this._getProviderCode(checkedRadio);
        // const paymentMethodId = this._getPaymentMethodIdFromRadio(checkedRadio);
        // const operation = this._getOperationFromRadio(checkedRadio);
        const inlineForm = this._getInlineForm(checkedRadio);
        const tokenizeCheckbox = inlineForm?.querySelector('[name="o_payment_tokenize_checkbox"]');

        // this._hideError(); // Don't keep the error displayed if the user is going through 3DS2 TODO problably useless now that we use a dialog
        this._disableButton(true); // Block the entire UI to prevent fiddling with other widgets.

        // TODO
        if (flow === 'token' && this.txContext['assign_token_route']) { // Token must be assigned.
            await this._assignToken(paymentOptionId); // TODO
        } else { // Both tokens and payment methods must process a payment operation.
            this.txContext.tokenizationRequested = tokenizeCheckbox?.checked ?? false;
            await this._processPaymentFlow(flow, providerCode, paymentOptionId);
        }
    },

    // #=== DOM MANIPULATION ===#

    /**
     * Check if the submit button can be enabled and do it if so.
     *
     * The UI is also unblocked in case it had been blocked.
     *
     * @private
     * @return {boolean} Whether the button was enabled.
     */
    _enableButton() {
        if (this._canSubmit()) {
            this._getSubmitButton().removeAttribute('disabled');
            return true;
        }
        $('body').unblock(); // TODO seems to work only when called from the console...
        return false;
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

        // Extract contextual values from the radio button.
        const flow = this._getPaymentFlow(radio);
        const paymentOptionId = this._getPaymentOptionId(radio);
        const providerCode = this._getProviderCode(radio);

        // Prepare the inline form of the selected payment option.
        await this._prepareInlineForm(providerCode, paymentOptionId, flow);

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
     * @param {number} paymentOptionId - The id of the selected payment option.
     * @param {string} flow - The payment flow of the selected payment option.
     * @return {void}
     */
    async _prepareInlineForm(providerCode, paymentOptionId, flow) {},

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
     * Display an error dialog in the payment form. TODO rewrite TODO only as dialog
     *
     * If no payment option is selected, the error is displayed in a dialog. If exactly one
     * payment option is selected, the error is displayed in the inline form of that payment
     * option and the view is focused on the error.
     *
     * @private
     * @param {string} title - The title of the error
     * @param {string} description - The description of the error
     * @param {string} error - The raw error message
     * @return {(Dialog|void)} A dialog showing the error, only when no payment option is selected.
     */
    _displayErrorDialog(title, description = '', error = '') {
        const checkedRadios = this.$('input[name="o_payment_radio"]:checked');
        if (checkedRadios.length !== 1) { // Cannot find selected payment option, show dialog
            return new Dialog(null, {
                title: sprintf(_t("Error: %s"), title),
                size: 'medium',
                $content: `<p>${escape(description) || ''}</p>`,
                buttons: [{text: _t("Ok"), close: true}]
            }).open();
        } else { // Show error in inline form
            this._hideError(); // Remove any previous error

            // Build the html for the error
            let errorHtml = `<div class="alert alert-danger mb4" name="o_payment_error_dialog">
                             <b>${escape(title)}</b>`;
            if (description !== '') {
                errorHtml += `</br>${escape(description)}`;
            }
            if (error !== '') {
                errorHtml += `</br>${escape(error)}`;
            }
            errorHtml += '</div>';

            // Append error to inline form and center the page on the error
            const $inlineForm = this._getInlineFormFromRadio(checkedRadios[0]);
            $inlineForm.removeClass('d-none'); // Show the inline form even if it was empty
            $inlineForm.append(errorHtml).find('div[name="o_payment_error_dialog"]')[0]
                .scrollIntoView({behavior: 'smooth', block: 'center'});
        }
        this._enableButton(); // Enable button back after it was disabled before processing TODO should be done in the guardedCatch of the processing methods
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
     * For a provider to do pre-processing work on the transaction processing flow, or to define its
     * entire own flow that requires re-scheduling the RPC to the transaction route, it must
     * override this method. If only post-processing work is needed, an override of
     * `_processRedirectPayment`,`_processDirectPayment` or `_processTokenPayment` might be more
     * appropriate. TODO
     *
     * @private
     * @param {string} flow - The payment flow of the selected payment option.
     * @param {string} providerCode - The code of the selected payment option's provider.
     * @param {number} paymentOptionId - The id of the selected payment option.
     * @return {void}
     */
    _processPaymentFlow(flow, providerCode, paymentOptionId) {
        // Create a transaction and retrieve its processing values.
        // this._rpc({
        //     route: this.txContext['transactionRoute'],
        //     params: this._prepareTransactionRouteParams(
        //         code, paymentOptionId, paymentMethodId, operation
        //     ),
        // }).then(processingValues => {
        //     if (operation === 'online_redirect') {
        //         this._processRedirectPayment(code, paymentOptionId, processingValues);
        //     } else if (operation === 'direct') {
        //         // TODO ANV
        //     } else if (operation === 'token') {
        //         // TODO ANV
        //     }
        // }).guardedCatch(error => {
        //     error.event.preventDefault();
        //     // this._displayError(
        //     //     _t("Server Error"),
        //     //     _t("We are not able to process your payment."),
        //     //     error.message.data.message,
        //     // ); TODO ANV
        // });
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
        const paymentOptionType = radio.dataset['paymentOptionType'];
        if (paymentOptionType === 'token' || this.txContext.flow === 'token') { // TODO when is the operation overriding the select option?
            return 'token';
        } else if (this.txContext.flow === 'redirect') {
            return 'redirect';
        } else {
            return 'direct';
        }
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
     * Determine and return the code of the provider of the selected payment option.
     *
     * @private
     * @param {HTMLElement} radio - The radio button linked to the payment option.
     * @return {string} The code of the provider of the selected payment option.
     */
    _getProviderCode(radio) {
        return radio.dataset['providerCode'];
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
    //         'flow': 'redirect',
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
