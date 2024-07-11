/** @odoo-module **/

import { Component } from '@odoo/owl';
import publicWidget from '@web/legacy/js/public/public_widget';
import { browser } from '@web/core/browser/browser';
import { ConfirmationDialog } from '@web/core/confirmation_dialog/confirmation_dialog';
import { _t } from '@web/core/l10n/translation';
import { renderToMarkup } from '@web/core/utils/render';
import { RPCError } from '@web/core/network/rpc_service';

publicWidget.registry.PaymentForm = publicWidget.Widget.extend({
    selector: '#o_payment_form',
    events: Object.assign({}, publicWidget.Widget.prototype.events, {
        'click [name="o_payment_radio"]': '_selectPaymentOption',
        'click [name="o_payment_delete_token"]': '_fetchTokenData',
        'click [name="o_payment_expand_button"]': '_hideExpandButton',
        'click [name="o_payment_submit_button"]': '_submitForm',
    }),

    // #=== WIDGET LIFECYCLE ===#

    /**
     * @override
     */
    init() {
        this._super(...arguments);
        this.rpc = this.bindService("rpc");
        this.orm = this.bindService("orm");
    },

    /**
     * @override
     */
    async start() {
        // Synchronously initialize paymentContext before any await.
        this.paymentContext = {};
        Object.assign(this.paymentContext, this.el.dataset);

        await this._super(...arguments);

        // Expand the payment form of the selected payment option if there is only one.
        const checkedRadio = document.querySelector('input[name="o_payment_radio"]:checked');
        if (checkedRadio) {
            await this._expandInlineForm(checkedRadio);
            this._enableButton(false);
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
        this._enableButton(false);
    },

    /**
     * Fetch data relative to the documents linked to the token and delegate them to the token
     * deletion confirmation dialog.
     *
     * @private
     * @param {Event} ev
     * @return {void}
     */
    _fetchTokenData(ev) {
        ev.preventDefault();

        const linkedRadio = document.getElementById(ev.currentTarget.dataset['linkedRadio']);
        const tokenId = this._getPaymentOptionId(linkedRadio);
        this.orm.call(
            'payment.token',
            'get_linked_records_info',
            [tokenId],
        ).then(linkedRecordsInfo => {
            this._challengeTokenDeletion(tokenId, linkedRecordsInfo);
        }).catch(error => {
            if (error instanceof RPCError) {
                this._displayErrorDialog(
                    _t("Cannot delete payment method"), error.data.message
                );
            } else {
                return Promise.reject(error);
            }
        });
    },

    /**
     * Hide the button to expand the payment methods section once it has been clicked.
     *
     * @private
     * @param {Event} ev
     * @return {void}
     */
    _hideExpandButton(ev) {
        ev.target.classList.add('d-none');
    },

    /**
     * Update the payment context with the selected payment option and initiate its payment flow.
     *
     * @private
     * @param {Event} ev
     * @return {void}
     */
    async _submitForm(ev) {
        ev.stopPropagation();
        ev.preventDefault();

        const checkedRadio = this.el.querySelector('input[name="o_payment_radio"]:checked');

        // Block the entire UI to prevent fiddling with other widgets.
        this._disableButton(true);

        // Initiate the payment flow of the selected payment option.
        const flow = this.paymentContext.flow = this._getPaymentFlow(checkedRadio);
        const paymentOptionId = this.paymentContext.paymentOptionId = this._getPaymentOptionId(
            checkedRadio
        );
        if (flow === 'token' && this.paymentContext['assignTokenRoute']) { // Assign token flow.
            await this._assignToken(paymentOptionId);
        } else { // Both tokens and payment methods must process a payment operation.
            const providerCode = this.paymentContext.providerCode = this._getProviderCode(
                checkedRadio
            );
            const pmCode = this.paymentContext.paymentMethodCode = this._getPaymentMethodCode(
                checkedRadio
            );
            this.paymentContext.providerId = this._getProviderId(checkedRadio);
            if (this._getPaymentOptionType(checkedRadio) === 'token') {
                this.paymentContext.tokenId = paymentOptionId;
            } else { // 'payment_method'
                this.paymentContext.paymentMethodId = paymentOptionId;
            }
            const inlineForm = this._getInlineForm(checkedRadio);
            this.paymentContext.tokenizationRequested = inlineForm?.querySelector(
                '[name="o_payment_tokenize_checkbox"]'
            )?.checked ?? this.paymentContext['mode'] === 'validation';
            await this._initiatePaymentFlow(providerCode, paymentOptionId, pmCode, flow);
        }
    },

    // #=== DOM MANIPULATION ===#

    /**
     * Check if the submit button can be enabled and do it if so.
     *
     * @private
     * @param {boolean} unblockUI - Whether the UI should also be unblocked.
     * @return {void}
     */
    _enableButton(unblockUI = true) {
        Component.env.bus.trigger('enablePaymentButton');
        if (unblockUI) {
            this.call('ui', 'unblock');
        }
    },

    /**
     * Disable the submit button.
     *
     * @private
     * @param {boolean} blockUI - Whether the UI should also be blocked.
     * @return {void}
     */
    _disableButton(blockUI = false) {
        Component.env.bus.trigger('disablePaymentButton');
        if (blockUI) {
            this.call('ui', 'block');
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
        tokenizeContainer?.classList.remove('d-none');

        // Show the submit button.
        Component.env.bus.trigger('showPaymentButton');
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
        tokenizeContainer?.classList.add('d-none');

        // Hide the submit button.
        Component.env.bus.trigger('hidePaymentButton');
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
        this._setPaymentFlow(); // Reset the payment flow to let providers overwrite it.

        // Prepare the inline form of the selected payment option.
        const providerId = this._getProviderId(radio);
        const providerCode = this._getProviderCode(radio);
        const paymentOptionId = this._getPaymentOptionId(radio);
        const paymentMethodCode = this._getPaymentMethodCode(radio);
        const flow = this._getPaymentFlow(radio);
        await this._prepareInlineForm(
            providerId, providerCode, paymentOptionId, paymentMethodCode, flow
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
     * @param {number} providerId - The id of the selected payment option's provider.
     * @param {string} providerCode - The code of the selected payment option's provider.
     * @param {number} paymentOptionId - The id of the selected payment option.
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {string} flow - The online payment flow of the selected payment option.
     * @return {void}
     */
    async _prepareInlineForm(providerId, providerCode, paymentOptionId, paymentMethodCode, flow) {},

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
     * @param {string} title - The title of the dialog.
     * @param {string} errorMessage - The error message.
     * @return {void}
     */
    _displayErrorDialog(title, errorMessage = '') {
        this.call('dialog', 'add', ConfirmationDialog, { title: title, body: errorMessage || "" });
    },

    /**
     * Display the token deletion confirmation dialog.
     *
     * @private
     * @param {number} tokenId - The id of the token whose deletion was requested.
     * @param {object} linkedRecordsInfo - The data relative to the documents linked to the token.
     * @return {void}
     */
    _challengeTokenDeletion(tokenId, linkedRecordsInfo) {
        const body = renderToMarkup('payment.deleteTokenDialog', { linkedRecordsInfo });
        this.call('dialog', 'add', ConfirmationDialog, {
            title: _t("Warning!"),
            body,
            confirmLabel: _t("Confirm Deletion"),
            confirm: () => this._archiveToken(tokenId),
            cancel: () => {},
        });
    },

    // #=== PAYMENT FLOW ===#

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
            this.paymentContext.flow = flow;
        } else {
            console.warn(`The value ${flow} is not a supported flow. Falling back to redirect.`);
            this.paymentContext.flow = 'redirect';
        }
    },

    /**
     * Assign the selected token to a document through the `assignTokenRoute`.
     *
     * @private
     * @param {number} tokenId - The id of the token to assign.
     * @return {void}
     */
    async _assignToken(tokenId) {
        this.rpc(this.paymentContext['assignTokenRoute'], {
            'token_id': tokenId,
            'access_token': this.paymentContext['accessToken'],
        }).then(() => {
            window.location = this.paymentContext['landingRoute'];
        }).catch(error => {
            if (error instanceof RPCError) {
                this._displayErrorDialog(_t("Cannot save payment method"), error.data.message);
                this._enableButton(); // The button has been disabled before initiating the flow.
            } else {
                return Promise.reject(error);
            }
        });
    },

    /**
     * Make an RPC to initiate the payment flow by creating a new transaction.
     *
     * For a provider to do pre-processing work (e.g., perform checks on the form inputs), or to
     * process the payment flow in its own terms (e.g., re-schedule the RPC to the transaction
     * route), it must override this method.
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
        this.rpc(
            this.paymentContext['transactionRoute'],
            this._prepareTransactionRouteParams(),
        ).then(processingValues => {
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
        }).catch(error => {
            if (error instanceof RPCError) {
                this._displayErrorDialog(_t("Payment processing failed"), error.data.message);
                this._enableButton(); // The button has been disabled before initiating the flow.
            } else {
                return Promise.reject(error);
            }
        });
    },

    /**
     * Prepare the params for the RPC to the transaction route.
     *
     * @private
     * @return {object} The transaction route params.
     */
    _prepareTransactionRouteParams() {
        let transactionRouteParams = {
            'provider_id': this.paymentContext.providerId,
            'payment_method_id': this.paymentContext.paymentMethodId ?? null,
            'token_id': this.paymentContext.tokenId ?? null,
            'amount': this.paymentContext['amount'] !== undefined
                ? parseFloat(this.paymentContext['amount']) : null,
            'flow': this.paymentContext['flow'],
            'tokenization_requested': this.paymentContext['tokenizationRequested'],
            'landing_route': this.paymentContext['landingRoute'],
            'is_validation': this.paymentContext['mode'] === 'validation',
            'access_token': this.paymentContext['accessToken'],
            'csrf_token': odoo.csrf_token,
        };
        // Generic payment flows (i.e., that are not attached to a document) require extra params.
        if (this.paymentContext['transactionRoute'] === '/payment/transaction') {
            Object.assign(transactionRouteParams, {
                'currency_id': this.paymentContext['currencyId']
                    ? parseInt(this.paymentContext['currencyId']) : null,
                'partner_id': parseInt(this.paymentContext['partnerId']),
                'reference_prefix': this.paymentContext['referencePrefix']?.toString(),
            });
        }
        return transactionRouteParams;
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
    _processRedirectFlow(providerCode, paymentOptionId, paymentMethodCode, processingValues) {
        // Create and configure the form element with the content rendered by the server.
        const div = document.createElement('div');
        div.innerHTML = processingValues['redirect_form_html'];
        const redirectForm = div.querySelector('form');
        redirectForm.setAttribute('id', 'o_payment_redirect_form');
        redirectForm.setAttribute('target', '_top');  // Ensures redirections when in an iframe.

        // Submit the form.
        document.body.appendChild(redirectForm);
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

    /**
     * Archive the provided token.
     *
     * @private
     * @param {number} tokenId - The id of the token whose deletion was requested.
     * @return {void}
     */
    _archiveToken(tokenId) {
        this.rpc('/payment/archive_token', {
            'token_id': tokenId,
        }).then(() => {
            browser.location.reload();
        }).catch(error => {
            if (error instanceof RPCError) {
                this._displayErrorDialog(
                    _t("Cannot delete payment method"), error.data.message
                );
            } else {
                return Promise.reject(error);
            }
        });
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
     * Determine and return the payment flow of the selected payment option.
     *
     * As some providers implement both direct payments and the payment with redirection flow, we
     * cannot infer it from the radio button only. The radio button indicates only whether the
     * payment option is a token. If not, the payment context is looked up to determine whether the
     * flow is 'direct' or 'redirect'.
     *
     * @private
     * @param {HTMLInputElement} radio - The radio button linked to the payment option.
     * @return {string} The flow of the selected payment option: 'redirect', 'direct' or 'token'.
     */
    _getPaymentFlow(radio) {
        // The flow is read from the payment context too in case it was forced in a custom implem.
        if (this._getPaymentOptionType(radio) === 'token' || this.paymentContext.flow === 'token') {
            return 'token';
        } else if (this.paymentContext.flow === 'redirect') {
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
     * Determine and return the id of the provider of the selected payment option.
     *
     * @private
     * @param {HTMLElement} radio - The radio button linked to the payment option.
     * @return {number} The id of the provider of the selected payment option.
     */
    _getProviderId(radio) {
        return Number(radio.dataset['providerId']);
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
     * Determine and return the state of the provider of the selected payment option.
     *
     * @private
     * @param {HTMLElement} radio - The radio button linked to the payment option.
     * @return {string} The state of the provider of the selected payment option.
     */
    _getProviderState(radio) {
        return radio.dataset['providerState'];
    },

});

export default publicWidget.registry.PaymentForm;
