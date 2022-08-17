odoo.define('payment.payment_form_mixin', require => {
    'use strict';

    const core = require('web.core');
    const Dialog = require('web.Dialog');

    const _t = core._t;

    return {

        /**
         * @override
         */
        start: async function () {
            await this._super(...arguments);
            window.addEventListener('pageshow', function (event) {
                if (event.persisted) {
                    window.location.reload();
                }
            });
            this.$('[data-bs-toggle="tooltip"]').tooltip();
            this.txContext = {};
            Object.assign(this.txContext, this.$el.data());
            const $checkedRadios = this.$('input[name="o_payment_radio"]:checked');
            if ($checkedRadios.length === 1) {
                const checkedRadio = $checkedRadios[0];
                this._displayInlineForm(checkedRadio);
                this._enableButton();
            } else {
                this._setPaymentFlow(); // Initialize the payment flow to let providers overwrite it
            }
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * Disable the submit button.
         *
         * The icons are updated to either show that an action is processing or that the button is
         * not ready, depending on the value of `showLoadingAnimation`.
         *
         * @private
         * @param {boolean} showLoadingAnimation - Whether a spinning loader should be shown
         * @return {undefined}
         */
        _disableButton: (showLoadingAnimation = true) => {
            const $submitButton = this.$('button[name="o_payment_submit_button"]');
            const iconClass = $submitButton.data('icon-class');
            $submitButton.attr('disabled', true);
            if (showLoadingAnimation) {
                $submitButton.find('i').removeClass(iconClass);
                $submitButton.prepend(
                    '<span class="o_loader"><i class="fa fa-refresh fa-spin"></i>&nbsp;</span>'
                );
            }
        },

        /**
         * Display an error in the payment form.
         *
         * If no payment option is selected, the error is displayed in a dialog. If exactly one
         * payment option is selected, the error is displayed in the inline form of that payment
         * option and the view is focused on the error.
         *
         * @private
         * @param {string} title - The title of the error
         * @param {string} description - The description of the error
         * @param {string} error - The raw error message
         * @return {(Dialog|undefined)} A dialog showing the error if no payment option is selected,
         *                              undefined otherwise.
         */
        _displayError: function (title, description = '', error = '') {
            const $checkedRadios = this.$('input[name="o_payment_radio"]:checked');
            if ($checkedRadios.length !== 1) { // Cannot find selected payment option, show dialog
                return new Dialog(null, {
                    title: _.str.sprintf(_t("Error: %s"), title),
                    size: 'medium',
                    $content: `<p>${_.str.escapeHTML(description) || ''}</p>`,
                    buttons: [{text: _t("Ok"), close: true}]
                }).open();
            } else { // Show error in inline form
                this._hideError(); // Remove any previous error

                // Build the html for the error
                let errorHtml = `<div class="alert alert-danger mb4" name="o_payment_error">
                                 <b>${_.str.escapeHTML(title)}</b>`;
                if (description !== '') {
                    errorHtml += `</br>${_.str.escapeHTML(description)}`;
                }
                if (error !== '') {
                    errorHtml += `</br>${_.str.escapeHTML(error)}`;
                }
                errorHtml += '</div>';

                // Append error to inline form and center the page on the error
                const checkedRadio = $checkedRadios[0];
                const paymentOptionId = this._getPaymentOptionIdFromRadio(checkedRadio);
                const formType = $(checkedRadio).data('payment-option-type');
                const $inlineForm = this.$(`#o_payment_${formType}_inline_form_${paymentOptionId}`);
                $inlineForm.removeClass('d-none'); // Show the inline form even if it was empty
                $inlineForm.append(errorHtml).find('div[name="o_payment_error"]')[0]
                    .scrollIntoView({behavior: 'smooth', block: 'center'});
            }
            this._enableButton(); // Enable button back after it was disabled before processing
            $('body').unblock(); // The page is blocked at this point, unblock it
        },

        /**
         * Display the inline form of the selected payment option and hide others.
         *
         * @private
         * @param {HTMLInputElement} radio - The radio button linked to the payment option
         * @return {undefined}
         */
        _displayInlineForm: function (radio) {
            this._hideInlineForms(); // Collapse previously opened inline forms
            this._hideError(); // The error is only relevant until it is hidden with its inline form
            this._setPaymentFlow(); // Reset the payment flow to let providers overwrite it

            // Extract contextual values from the radio button
            const provider = this._getProviderFromRadio(radio);
            const paymentOptionId = this._getPaymentOptionIdFromRadio(radio);
            const flow = this._getPaymentFlowFromRadio(radio);

            // Prepare the inline form of the selected payment option and display it if not empty
            this._prepareInlineForm(provider, paymentOptionId, flow);
            const formType = $(radio).data('payment-option-type');
            const $inlineForm = this.$(`#o_payment_${formType}_inline_form_${paymentOptionId}`);
            if ($inlineForm.children().length > 0) {
                $inlineForm.removeClass('d-none');
            }
        },

        /**
         * Check if the submit button can be enabled and do it if so.
         *
         * The icons are updated to show that the button is ready.
         *
         * @private
         * @return {boolean} Whether the button was enabled.
         */
        _enableButton: function () {
            if (this._isButtonReady()) {
                const $submitButton = this.$('button[name="o_payment_submit_button"]');
                const iconClass = $submitButton.data('icon-class');
                $submitButton.attr('disabled', false);
                $submitButton.find('i').addClass(iconClass);
                $submitButton.find('span.o_loader').remove();
                return true;
            }
            return false;
        },

        /**
         * Verify that exactly one radio button is checked and display an error otherwise.
         *
         * @private
         * @param {jQuery} $checkedRadios - The currently check radio buttons
         *
         * @return {boolean} Whether exactly one radio button among the provided radios is checked
         */
        _ensureRadioIsChecked: function ($checkedRadios) {
            if ($checkedRadios.length === 0) {
                this._displayError(
                    _t("No payment option selected"),
                    _t("Please select a payment option.")
                );
                return false;
            } else if ($checkedRadios.length > 1) {
                this._displayError(
                    _t("Multiple payment options selected"),
                    _t("Please select only one payment option.")
                );
                return false;
            }
            return true;
        },

        /**
         * Determine and return the online payment flow of the selected payment option.
         *
         * As some providers implement both the direct payment and the payment with redirection, the
         * flow cannot be inferred from the radio button only. The radio button only indicates
         * whether the payment option is a token. If not, the transaction context is looked up to
         * determine whether the flow is 'direct' or 'redirect'.
         *
         * @private
         * @param {HTMLInputElement} radio - The radio button linked to the payment option
         * @return {string} The flow of the selected payment option. redirect, direct or token.
         */
        _getPaymentFlowFromRadio: function (radio) {
            if (
                $(radio).data('payment-option-type') === 'token'
                || this.txContext.flow === 'token'
            ) {
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
         * @param {HTMLInputElement} radio - The radio button linked to the payment option
         * @return {number} The provider id or the token id or of the payment option linked to the
         *                  radio button.
         */
        _getPaymentOptionIdFromRadio: radio => $(radio).data('payment-option-id'),

        /**
         * Determine and return the provider of the selected payment option.
         *
         * @private
         * @param {HTMLInputElement} radio - The radio button linked to the payment option
         * @return {number} The provider of the payment option linked to the radio button.
         */
        _getProviderFromRadio: radio => $(radio).data('provider'),

        /**
         * Remove the error in the provider form.
         *
         * @private
         * @return {jQuery} The removed error
         */
        _hideError: () => this.$('div[name="o_payment_error"]').remove(),

        /**
         * Collapse all inline forms.
         *
         * @private
         * @return {undefined}.
         */
        _hideInlineForms: () => this.$('[name="o_payment_inline_form"]').addClass('d-none'),

        /**
         * Hide the "Save my payment details" label and checkbox, and the submit button.
         *
         * The inputs should typically be hidden when the customer has to perform additional actions
         * in the inline form. All inputs are automatically shown again when the customer clicks on
         * another inline form.
         *
         * @private
         * @return {undefined}
         */
        _hideInputs: function () {
            const $submitButton = this.$('button[name="o_payment_submit_button"]');
            const $tokenizeCheckboxes = this.$('input[name="o_payment_save_as_token"]');
            $submitButton.addClass('d-none');
            $tokenizeCheckboxes.closest('label').addClass('d-none');
        },

        /**
         * Verify that the submit button is ready to be enabled.
         *
         * For a module to support a custom behavior for the submit button, it must override this
         * method and only return true if the result of this method is true and if nothing prevents
         * enabling the submit button for that custom behavior.
         *
         * @private
         *
         * @return {boolean} Whether the submit button can be enabled
         */
        _isButtonReady: function () {
            const $checkedRadios = this.$('input[name="o_payment_radio"]:checked');
            if ($checkedRadios.length === 1) {
                const checkedRadio = $checkedRadios[0];
                const flow = this._getPaymentFlowFromRadio(checkedRadio);
                return flow !== 'token' || this.txContext.allowTokenSelection;
            } else {
                return false;
            }
        },

        /**
         * Prepare the params to send to the transaction route.
         *
         * For a provider to overwrite generic params or to add provider-specific ones, it must
         * override this method and return the extended transaction route params.
         *
         * @private
         * @param {string} code - The code of the selected payment option provider
         * @param {number} paymentOptionId - The id of the selected payment option
         * @param {string} flow - The online payment flow of the selected payment option
         * @return {object} The transaction route params
         */
        _prepareTransactionRouteParams: function (code, paymentOptionId, flow) {
            return {
                'payment_option_id': paymentOptionId,
                'reference_prefix': this.txContext.referencePrefix !== undefined
                    ? this.txContext.referencePrefix.toString() : null,
                'amount': this.txContext.amount !== undefined
                    ? parseFloat(this.txContext.amount) : null,
                'currency_id': this.txContext.currencyId
                    ? parseInt(this.txContext.currencyId) : null,
                'partner_id': parseInt(this.txContext.partnerId),
                'flow': flow,
                'tokenization_requested': this.txContext.tokenizationRequested,
                'landing_route': this.txContext.landingRoute,
                'is_validation': this.txContext.isValidation,
                'access_token': this.txContext.accessToken
                    ? this.txContext.accessToken : undefined,
                'csrf_token': core.csrf_token,
            };
        },

        /**
         * Prepare the provider-specific inline form of the selected payment option.
         *
         * For a provider to manage an inline form, it must override this method. When the override
         * is called, it must lookup the parameters to decide whether it is necessary to prepare its
         * inline form. Otherwise, the call must be sent back to the parent method.
         *
         * @private
         * @param {string} code - The code of the selected payment option's provider
         * @param {number} paymentOptionId - The id of the selected payment option
         * @param {string} flow - The online payment flow of the selected payment option
         * @return {Promise}
         */
        _prepareInlineForm: (code, paymentOptionId, flow) => Promise.resolve(),

        /**
         * Process the payment.
         *
         * For a provider to do pre-processing work on the transaction processing flow, or to
         * define its entire own flow that requires re-scheduling the RPC to the transaction route,
         * it must override this method.
         * If only post-processing work is needed, an override of `_processRedirectPayment`,
         * `_processDirectPayment` or `_processTokenPayment` might be more appropriate.
         *
         * @private
         * @param {string} code - The code of the payment option's provider
         * @param {number} paymentOptionId - The id of the payment option handling the transaction
         * @param {string} flow - The online payment flow of the transaction
         * @return {Promise}
         */
        _processPayment: function (code, paymentOptionId, flow) {
            // Call the transaction route to create a tx and retrieve the processing values
            return this._rpc({
                route: this.txContext.transactionRoute,
                params: this._prepareTransactionRouteParams(code, paymentOptionId, flow),
            }).then(processingValues => {
                if (flow === 'redirect') {
                    return this._processRedirectPayment(
                        code, paymentOptionId, processingValues
                    );
                } else if (flow === 'direct') {
                    return this._processDirectPayment(code, paymentOptionId, processingValues);
                } else if (flow === 'token') {
                    return this._processTokenPayment(code, paymentOptionId, processingValues);
                }
            }).guardedCatch(error => {
                error.event.preventDefault();
                this._displayError(
                    _t("Server Error"),
                    _t("We are not able to process your payment."),
                    error.message.data.message
                );
            });
        },

        /**
         * Execute the provider-specific implementation of the direct payment flow.
         *
         * For a provider to redefine the processing of the direct payment flow, it must override
         * this method.
         *
         * @private
         * @param {string} code - The code of the provider
         * @param {number} providerId - The id of the provider handling the transaction
         * @param {object} processingValues - The processing values of the transaction
         * @return {Promise}
         */
        _processDirectPayment: (code, providerId, processingValues) => Promise.resolve(),

        /**
         * Redirect the customer by submitting the redirect form included in the processing values.
         *
         * For a provider to redefine the processing of the payment with redirection flow, it must
         * override this method.
         *
         * @private
         * @param {string} code - The code of the provider
         * @param {number} providerId - The id of the provider handling the transaction
         * @param {object} processingValues - The processing values of the transaction
         * @return {undefined}
         */
        _processRedirectPayment: (code, providerId, processingValues) => {
            // Append the redirect form to the body
            const $redirectForm = $(processingValues.redirect_form_html).attr(
                'id', 'o_payment_redirect_form'
            );
            $(document.getElementsByTagName('body')[0]).append($redirectForm);

            // Submit the form
            $redirectForm.submit();
        },

        /**
         * Redirect the customer to the status route.
         *
         * For a provider to redefine the processing of the payment by token flow, it must override
         * this method.
         *
         * @private
         * @param {string} provider_code - The code of the token's provider
         * @param {number} tokenId - The id of the token handling the transaction
         * @param {object} processingValues - The processing values of the transaction
         * @return {undefined}
         */
        _processTokenPayment: (provider_code, tokenId, processingValues) => {
            // The flow is already completed as payments by tokens are immediately processed
            window.location = '/payment/status';
        },

        /**
         * Set the online payment flow for the selected payment option.
         *
         * For a provider to manage direct payments, it must call this method from within its
         * override of `_prepareInlineForm` to declare its payment flow for the selected payment
         * option.
         *
         * @private
         * @param {string} flow - The flow for the selected payment option. Either 'redirect',
         *                        'direct' or 'token'
         * @return {undefined}
         */
        _setPaymentFlow: function (flow = 'redirect') {
            if (flow !== 'redirect' && flow !== 'direct' && flow !== 'token') {
                console.warn(
                    `payment_form_mixin: method '_setPaymentFlow' was called with invalid flow: 
                    ${flow}. Falling back to 'redirect'.`
                );
                this.txContext.flow = 'redirect';
            } else {
                this.txContext.flow = flow;
            }
        },

        /**
         * Show the "Save my payment details" label and checkbox, and the submit button.
         *
         * @private
         * @return {undefined}.
         */
        _showInputs: function () {
            const $submitButton = this.$('button[name="o_payment_submit_button"]');
            const $tokenizeCheckboxes = this.$('input[name="o_payment_save_as_token"]');
            $submitButton.removeClass('d-none');
            $tokenizeCheckboxes.closest('label').removeClass('d-none');
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * Hide all extra payment icons of the provider linked to the clicked button.
         *
         * Called when clicking on the "show less" button.
         *
         * @private
         * @param {Event} ev
         * @return {undefined}
         */
        _onClickLessPaymentIcons: ev => {
            ev.preventDefault();
            ev.stopPropagation();
            // Hide the extra payment icons, and the "show less" button
            const $itemList = $(ev.currentTarget).parents('ul');
            const maxIconNumber = $itemList.data('max-icons');
            $itemList.children('li').slice(maxIconNumber).addClass('d-none');
            // Show the "show more" button
            $itemList.find('a[name="o_payment_icon_more"]').parents('li').removeClass('d-none');
        },

        /**
         * Display all the payment icons of the provider linked to the clicked button.
         *
         * Called when clicking on the "show more" button.
         *
         * @private
         * @param {Event} ev
         * @return {undefined}
         */
        _onClickMorePaymentIcons: ev => {
            ev.preventDefault();
            ev.stopPropagation();
            // Display all the payment icons, and the "show less" button
            $(ev.currentTarget).parents('ul').children('li').removeClass('d-none');
            // Hide the "show more" button
            $(ev.currentTarget).parents('li').addClass('d-none');
        },

        /**
         * Mark the clicked card radio button as checked and open the inline form, if any.
         *
         * Called when clicking on the card of a payment option.
         *
         * @private
         * @param {Event} ev
         * @return {undefined}
         */
        _onClickPaymentOption: function (ev) {
            // Uncheck all radio buttons
            this.$('input[name="o_payment_radio"]').prop('checked', false);
            // Check radio button linked to selected payment option
            const checkedRadio = $(ev.currentTarget).find('input[name="o_payment_radio"]')[0];
            $(checkedRadio).prop('checked', true);

            // Show the inputs in case they had been hidden
            this._showInputs();

            // Disable the submit button while building the content
            this._disableButton(false);

            // Unfold and prepare the inline form of selected payment option
            this._displayInlineForm(checkedRadio);

            // Re-enable the submit button
            this._enableButton();
        },

    };

});
