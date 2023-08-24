/** @odoo-module **/

import { debounce } from '@web/core/utils/timing';
import publicWidget from '@web/legacy/js/public/public_widget';

import PaymentForm from '@payment/js/payment_form';

const websiteSalePaymentMixin = {

    // #=== WIDGET LIFECYCLE ===#

    /**
     * @override
     */
    init() {
        this._onClickTCCheckbox = debounce(this._onClickTCCheckbox, 100, true);
        this._super(...arguments);
    },

    prepareInputs() {
        this.$checkbox = $(document.getElementById('website_sale_tc_checkbox'));
        this.$submitButton = $(document.querySelector('[name="o_payment_submit_button"]'));
        this._adaptConfirmButton();
    },

    /**
     * Update the data on the submit button with the status of the Terms and Conditions input.
     *
     * @private
     * @return {void}
     */
    _adaptConfirmButton() {
        if (this.$checkbox.length > 0) {
            const disabledReasons = this.$submitButton.data('disabled_reasons') || {};
            disabledReasons.tc = !this.$checkbox.prop('checked');
            this.$submitButton.data('disabled_reasons', disabledReasons);
        }
    },

};

PaymentForm.include(Object.assign({}, websiteSalePaymentMixin, {

    // #=== WIDGET LIFECYCLE ===#

    /**
     * @override
     */
    async start() {
        this.prepareInputs();
        if (this.$checkbox.length > 0) { // The checkbox is outside the payment form.
            this.$checkbox[0].addEventListener('change', () => this._onClickTCCheckbox());
        }
        if (this.$submitButton.length > 0) {  // The button is outside the payment form.
            this.$submitButton[0].addEventListener('click', ev => this._submitForm(ev));
        }
        return await this._super(...arguments);
    },

    // #=== EVENT HANDLERS ===#

    /**
     * Enable the submit button if it all conditions are met.
     *
     * @private
     * @return {void}
     */
    _onClickTCCheckbox() {
        this._disableButton();
        this._adaptConfirmButton();
        this._enableButton();
    },

    // #=== PAYMENT FLOW ===#

    /**
     * Verify that the Terms and Condition checkbox is checked.
     *
     * @override method from @payment/js/payment_form
     * @private
     * @return {boolean} Whether the form can be submitted.
     */
    _canSubmit() {
        const disabledReasonFound = Object.values(
            this.$submitButton.data('disabled_reasons') || {}
        ).includes(true);
        return !disabledReasonFound && this._super();
    },

}));

publicWidget.registry.WebsiteSalePayment = publicWidget.Widget.extend(
    Object.assign({}, websiteSalePaymentMixin, {
        selector: 'div[name="o_website_sale_free_cart"]',
        events: {
            'change #website_sale_tc_checkbox': '_onClickTCCheckbox',
        },

        // #=== WIDGET LIFECYCLE ===#

        /**
         * @override
         */
        async start() {
            this.prepareInputs();
            this._onClickTCCheckbox();
            return await this._super(...arguments);
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * Enable the submit button if it all conditions are met.
         *
         * @private
         * @return {void}
         */
        _onClickTCCheckbox() {
            this._adaptConfirmButton();
            const disabledReasonFound = Object.values(
                this.$submitButton.data('disabled_reasons') || {}
            ).includes(true);
            this.$submitButton.prop('disabled', disabledReasonFound);
        },
    }));
