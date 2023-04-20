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
            this.$submitButton = this.$('button[name="o_payment_submit_button"]');
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
            const disabledReasonFound = this.$submitButton.data("disabled_reasons");
            return !disabledReasonFound && this._super();
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

    publicWidget.registry.WebsiteSalePayment = publicWidget.Widget.extend(
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
                this.$submitButton = this.$('button[name="o_payment_submit_button"]');
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
                const disabledReasonFound = this.$submitButton.data("disabled_reasons");
                this.$submitButton.prop('disabled', disabledReasonFound);
            },
        }));
