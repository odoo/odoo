odoo.define('payment.checkout_form', require => {
    'use strict';

    const publicWidget = require('web.public.widget');

    const paymentFormMixin = require('payment.payment_form_mixin');

    publicWidget.registry.PaymentCheckoutForm = publicWidget.Widget.extend(paymentFormMixin, {
        selector: 'form[name="o_payment_checkout"]',
        events: Object.assign({}, publicWidget.Widget.prototype.events, {
                'click div[name="o_payment_option_card"]': '_onClickPaymentOption',
                'click a[name="o_payment_icon_more"]': '_onClickMorePaymentIcons',
                'click a[name="o_payment_icon_less"]': '_onClickLessPaymentIcons',
                'click button[name="o_payment_submit_button"]': '_onClickPay',
                'submit': '_onSubmit',
            }),

        /**
         * @constructor
         */
        init: function () {
            const preventDoubleClick = handlerMethod => {
                return _.debounce(handlerMethod, 500, true);
            };
            this._super(...arguments);
            // Prevent double-clicks and browser glitches on all inputs
            this._onClickLessPaymentIcons = preventDoubleClick(this._onClickLessPaymentIcons);
            this._onClickMorePaymentIcons = preventDoubleClick(this._onClickMorePaymentIcons);
            this._onClickPay = preventDoubleClick(this._onClickPay);
            this._onClickPaymentOption = preventDoubleClick(this._onClickPaymentOption);
            this._onSubmit = preventDoubleClick(this._onSubmit);
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * Handle a direct payment, a payment with redirection, or a payment by token.
         *
         * Called when clicking on the 'Pay' button or when submitting the form.
         *
         * @private
         * @param {Event} ev
         * @return {undefined}
         */
        _onClickPay: async function (ev) {
            ev.stopPropagation();
            ev.preventDefault();

            // Check that the user has selected a payment option
            const $checkedRadios = this.$('input[type="radio"]:checked');
            if (!this._ensureRadioIsChecked($checkedRadios)) {
                return;
            }
            const checkedRadio = $checkedRadios[0];

            // Extract contextual values from the radio button
            const paymentOptionId = this._getPaymentOptionIdFromRadio(checkedRadio);
            const provider = this._getProviderFromRadio(checkedRadio);
            const flow = this._getPaymentFlowFromRadio(checkedRadio);

            // Update the tx context with the value of the "Save my payment details" checkbox
            this.txContext.tokenizationRequested = flow !== 'token'
                && this.$(`#o_payment_inline_form_${paymentOptionId}`).find(
                    'input[name="o_payment_save_as_token"]'
                )[0].checked;

            // Make the payment
            this._disableButton();
            this._processTx(paymentOptionId, provider, flow);
            this._enableButton();
        },

        /**
         * Delegate the handling of the payment request to `_onClickPay`.
         *
         * Called when submitting the form (e.g. through the Return key).
         *
         * @private
         * @param {Event} ev
         * @return {undefined}
         */
        _onSubmit: function (ev) {
            ev.stopPropagation();
            ev.preventDefault();

            this._onClickPay(ev);
        },

    });
    return publicWidget.registry.PaymentCheckoutForm;
});
