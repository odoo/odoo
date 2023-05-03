/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';
import paymentFormMixin from '@payment/js/payment_form_mixin';
import { debounce } from '@web/core/utils/timing';

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
        this.formType = 'checkout';
        const preventDoubleClick = handlerMethod => {
            return debounce(handlerMethod, 500, true);
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
     * @return {void}
     */
    _onClickPay: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();

        // Check that the user has selected a payment option
        const $checkedRadios = this.$('input[name="o_payment_radio"]:checked');
        if (!this._ensureRadioIsChecked($checkedRadios)) {
            return;
        }
        const checkedRadio = $checkedRadios[0];

        // Extract contextual values from the radio button
        const provider = this._getProviderFromRadio(checkedRadio);
        const paymentOptionId = this._getPaymentOptionIdFromRadio(checkedRadio);
        const flow = this._getPaymentFlowFromRadio(checkedRadio);

        // Update the tx context with the value of the "Save my payment details" checkbox
        if (flow !== 'token') {
            const $inlineForm = this._getInlineFormFromRadio(checkedRadio);
            const $tokenizeCheckbox = $inlineForm.find('input[name="o_payment_save_as_token"]');
            this.txContext.tokenizationRequested = $tokenizeCheckbox.length === 1
                && $tokenizeCheckbox[0].checked;
        } else {
            this.txContext.tokenizationRequested = false;
        }

        // Make the payment
        this._hideError(); // Don't keep the error displayed if the user is going through 3DS2
        this._disableButton(true); // Disable until it is needed again
        this.call('ui', 'block');
        this._processPayment(provider, paymentOptionId, flow);
    },

    /**
     * Delegate the handling of the payment request to `_onClickPay`.
     *
     * Called when submitting the form (e.g. through the Return key).
     *
     * @private
     * @param {Event} ev
     * @return {void}
     */
    _onSubmit: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();

        this._onClickPay(ev);
    },

});

export default publicWidget.registry.PaymentCheckoutForm;
