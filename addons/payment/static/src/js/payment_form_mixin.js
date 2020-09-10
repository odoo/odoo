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
            this.$('[data-toggle="tooltip"]').tooltip();
            this.txContext = {};
            Object.assign(this.txContext, this.$el.data());
            const $checkedRadios = this.$('input[type="radio"]:checked');
            if ($checkedRadios.length === 1) {
                const checkedRadio = $checkedRadios[0];
                this._displayInlineForm(checkedRadio);
                this._enableButton();
            } else {
                this._setPaymentFlow(); // Initialize the payment flow to let acquirers overwrite it
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
            const $checkedRadios = this.$('input[type="radio"]:checked');
            if ($checkedRadios.length !== 1) { // Cannot find selected payment option, show dialog
                return new Dialog(null, {
                    title: _.str.sprintf(_t("Error: %s"), _.str.escapeHTML(title)),
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
                const $inlineForm = this.$(`#o_payment_inline_form_${paymentOptionId}`);
                $inlineForm.removeClass('d-none'); // Show the inline form even if it was empty
                $inlineForm.append(errorHtml).find('div[name="o_payment_error"]')[0]
                    .scrollIntoView({behavior: 'smooth', block: 'center'});
            }
        },

        /**
         * Display the inline form of the selected payment option and hide others.
         *
         * @private
         * @param {HTMLInputElement} radio - The radio button linked to the payment option
         * @return {undefined}
         */
        _displayInlineForm: function (radio) {
            // Hide all inline forms
            this.$('[id*="o_payment_inline_form_"]').addClass('d-none');
            this._hideError();

            // Reset the payment flow to let acquirers overwrite it
            this._setPaymentFlow();

            // Extract contextual values from the radio button
            const paymentOptionId = this._getPaymentOptionIdFromRadio(radio);
            const provider = this._getProviderFromRadio(radio);
            const flow = this._getPaymentFlowFromRadio(radio);

            // Prepare the inline form of the selected payment option and display it if not empty
            this._prepareInlineForm(paymentOptionId, provider, flow);
            const $inlineForm = this.$(`#o_payment_inline_form_${paymentOptionId}`);
            if (!$inlineForm.is(':empty')) {
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
         * As some acquirers implement both the direct payment and the payment with redirection, the
         * flow cannot be inferred from the radio button only. The radio button only indicates
         * whether the payment option is a token. If not, the transaction context is looked up to
         * determine whether the flow is 'direct' or 'redirect'.
         *
         * @private
         * @param {HTMLInputElement} radio - The radio button linked to the payment option
         * @return {string} The flow of the selected payment option. redirect, direct or token.
         */
        _getPaymentFlowFromRadio: function (radio) {
            if ($(radio).data('is-token') || this.txContext.flow === 'token') {
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
         * @return {number} The acquirer id or the token id or of the payment option linked to the
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
         * Remove the error in the acquirer form.
         *
         * @private
         * @return {jQuery} The removed error
         */
        _hideError: () => this.$('div[name="o_payment_error"]').remove(),

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
            const $checkedRadios = this.$('input[type="radio"]:checked');
            if ($checkedRadios.length === 1) {
                const checkedRadio = $checkedRadios[0];
                const flow = this._getPaymentFlowFromRadio(checkedRadio);
                return flow !== 'token' || this.txContext.allowTokenSelection;
            } else {
                return false;
            }
        },

        /**
         * Prepare the acquirer-specific inline form of the selected payment option.
         *
         * For an acquirer to manage an inline form, it must override this method. When the override
         * is called, it must lookup the parameters to decide whether it is necessary to prepare its
         * inline form. Otherwise, the call must be sent back to the parent method.
         *
         * @private
         * @param {number} _paymentOptionId - The id of the selected payment option
         * @param {string} _provider - The provider of the selected payment option's acquirer
         * @param {string} _flow - The online payment flow of the selected payment option
         * @return {undefined}
         */
        _prepareInlineForm: (_paymentOptionId, _provider, _flow) => {},

        /**
         * Create and process the transaction.
         *
         * For an acquirer to define its own transaction processing flow, to do pre-processing work
         * or to do post-processing work, it must override this method.
         *
         * @private
         * @param {number} paymentOptionId - The id of the payment option handling the transaction
         * @param {string} _provider - The provider of the payment option's acquirer
         * @param {string} flow - The online payment flow of the transaction
         * @return {undefined}
         */
        _processTx: function (paymentOptionId, _provider, flow) {
            // Call the init route to initialize the transaction and retrieve processing values
            this._rpc({
                route: this.txContext.initTxRoute,
                params: {
                    'payment_option_id': paymentOptionId,
                    'reference': this.txContext.reference,
                    'amount': this.txContext.amount !== undefined
                        ? parseFloat(this.txContext.amount) : null,
                    'currency_id': this.txContext.currencyId
                        ? parseInt(this.txContext.currencyId) : null,
                    'partner_id': this.txContext.partnerId
                        ? parseInt(this.txContext.partnerId) : undefined,
                    'order_id': this.txContext.orderId
                        ? parseInt(this.txContext.orderId) : undefined,
                    'flow': flow,
                    'tokenization_requested': this.txContext.tokenizationRequested,
                    'is_validation': this.txContext.isValidation !== undefined
                        ? this.txContext.isValidation : false,
                    'landing_route': this.txContext.landingRoute,
                    'access_token': this.txContext.accessToken
                        ? this.txContext.accessToken : undefined,
                    'csrf_token': core.csrf_token,
                }
            }).then(result => {
                if (flow === 'redirect') {
                    // Append the redirect form to the body
                    const $redirectForm = $(result.redirect_form_html).attr(
                        'id', 'o_payment_redirect_form'
                    );
                    $(document.getElementsByTagName('body')[0]).append($redirectForm);

                    // Submit the form
                    $redirectForm.submit();
                } else if (flow === 'direct') {
                    // The direct flow is handled by acquirers in the override of this method
                } else if (flow === 'token') {
                    window.location = '/payment/status'; // Tokens have already been processed
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
         * Set the online payment flow for the selected payment option.
         *
         * For an acquirer to manage direct payments, it must call this method from within its
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

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * Hide all extra payment icons of the acquirer linked to the clicked button.
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
         * Display all the payment icons of the acquirer linked to the clicked button.
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
            this.$('input[type="radio"]').prop('checked', false);
            // Check radio button linked to selected payment option
            const checkedRadio = $(ev.currentTarget).find('input[type="radio"]')[0];
            $(checkedRadio).prop('checked', true);

            // Disable the submit button while building the content
            this._disableButton(false);

            // Unfold and prepare the inline form of selected payment option
            this._displayInlineForm(checkedRadio);

            // Re-enable the submit button
            this._enableButton();
        },

    };

});
