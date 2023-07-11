/** @odoo-module **/

    import { debounce } from "@web/core/utils/timing";
    import checkoutForm from "payment.checkout_form";
    import publicWidget from "web.public.widget";

    const websiteSalePaymentMixin = {

        /**
         * @override
         */
        init: function () {
            this._onClickTCCheckbox = debounce(this._onClickTCCheckbox, 100, true);
            this._super(...arguments);
        },

        /**
         * @override
         */
        start: function () {
            this.$checkbox = this.$('#checkbox_tc');
            this.$submitButton = this.$('button[name="o_wsale_payment_submit_button"]');
            this._adaptConfirmButton();
            return this._super(...arguments);
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * Update the data on the submit button with the status of the Terms and Conditions input.
         *
         * @private
         * @return {undefined}
         */
        _adaptConfirmButton: function () {
            if (this.$checkbox.length > 0) {
                const disabledReasons = this.$submitButton.data('disabled_reasons') || {};
                disabledReasons.tc = !this.$checkbox.prop('checked');
                this.$submitButton.data('disabled_reasons', disabledReasons);
            }
        },

    };

    checkoutForm.include(Object.assign({}, websiteSalePaymentMixin, {
        events: Object.assign({}, checkoutForm.prototype.events, {
            'change #checkbox_tc': '_onClickTCCheckbox',
        }),

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * Verify that the Terms and Condition checkbox is checked.
         *
         * @override method from payment.payment_form_mixin
         * @private
         * @return {boolean} Whether the submit button can be enabled
         */
        _isButtonReady: function () {
            const disabledReasonFound = Object.values(
                this.$submitButton.data("disabled_reasons") || {}
            ).includes(true);
            return !disabledReasonFound && this._super();
        },

        /**
         * In ecommerce, return the specific "Pay Now" button, which should be enable/disabled
         * according to the readiness of the payment form.
         *
         * @returns submit Button
         */
        _getSubmitButton() {
            const res = this._super();
            if (res.length > 0) {
                return res
            }
            return $('button[name="o_wsale_payment_submit_button"]');
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * Enable the submit button if it all conditions are met.
         *
         * @private
         * @return {undefined}
         */
        _onClickTCCheckbox: function () {
            this._adaptConfirmButton();

            if (!this._enableButton()) {
                this._disableButton(false);
            }
        },

    }));

    publicWidget.registry.WebsiteSalePaymentFreeCart = publicWidget.Widget.extend(
        Object.assign({}, websiteSalePaymentMixin, {
            selector: 'div[name="o_website_sale_free_cart"]',
            events: {
                'change #checkbox_tc': '_onClickTCCheckbox',
            },

            /**
             * @override
             */
            start: function () {
                this.$checkbox = this.$('#checkbox_tc');
                this.$submitButton = this.$('button[name="o_wsale_payment_submit_button"]');
                this._onClickTCCheckbox();
                return this._super(...arguments);
            },

            //--------------------------------------------------------------------------
            // Handlers
            //--------------------------------------------------------------------------

            /**
             * Enable the submit button if it all conditions are met.
             *
             * @private
             * @return {undefined}
             */
            _onClickTCCheckbox: function () {
                this._adaptConfirmButton();
                const disabledReasonFound = Object.values(
                    this.$submitButton.data("disabled_reasons") || {}
                ).includes(true);
                this.$submitButton.prop('disabled', disabledReasonFound);
            },
        }));

publicWidget.registry.WebsiteSalePayment = publicWidget.Widget.extend({
    selector: '.oe_website_sale',
    events: {
        'click button[name="o_wsale_payment_submit_button"]': '_onClickPayWebsiteSale',
    },

    /**
     * Submit the payment form when the custom 'Pay Now' button of ecommerce is clicked on
     *
     * @param {Event} ev
     */
    _onClickPayWebsiteSale(ev) {
        const $paymentform = $('form.o_payment_form');
        if ($paymentform.length == 1) {
            ev.preventDefault()
            $paymentform.submit()
        }
    },
});
