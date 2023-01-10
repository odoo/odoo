/** @odoo-module */

import core from 'web.core';
import publicWidget from 'web.public.widget';

publicWidget.registry.PaymentExpressCheckoutForm = publicWidget.Widget.extend({
    selector: 'form[name="o_payment_express_checkout_form"]',

    events: Object.assign({}, publicWidget.Widget.prototype.events, {
        'click button[name="o_payment_submit_button"]': '_onClickPay',
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
        this._onClickPay = preventDoubleClick(this._onClickPay);
    },

    /**
     * @override
     */
    start: async function () {
        await this._super(...arguments);
        this.txContext = {};
        Object.assign(this.txContext, this.$el.data());
        this.txContext.shippingInfoRequired = !!this.txContext.shippingInfoRequired;
        const expressCheckoutForms = this._getExpressCheckoutForms();
        for (const expressCheckoutForm of expressCheckoutForms) {
            await this._prepareExpressCheckoutForm(expressCheckoutForm.dataset);
        }
        // Monitor updates of the amount on eCommerce's cart pages.
        core.bus.on('cart_amount_changed', this, this._updateAmount.bind(this));
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Return all express checkout forms found on the page.
     *
     * @private
     * @return {NodeList} - All express checkout forms found on the page.
     */
    _getExpressCheckoutForms() {
        return document.querySelectorAll(
            'form[name="o_payment_express_checkout_form"] div[name="o_express_checkout_container"]'
        );
    },

    /**
     * Prepare the provider-specific express checkout form based on the provided data.
     *
     * For a provider to manage an express checkout form, it must override this method.
     *
     * @private
     * @param {Object} providerData - The provider-specific data.
     * @return {Promise}
     */
    async _prepareExpressCheckoutForm(providerData) {
        return Promise.resolve();
    },

    /**
     * Prepare the params to send to the transaction route.
     *
     * For a provider to overwrite generic params or to add provider-specific ones, it must override
     * this method and return the extended transaction route params.
     *
     * @private
     * @param {number} providerId - The id of the provider handling the transaction.
     * @returns {object} - The transaction route params
     */
    _prepareTransactionRouteParams(providerId) {
        return {
            'payment_option_id': parseInt(providerId),
            'reference_prefix': this.txContext.referencePrefix &&
                                this.txContent.referencePrefix.toString(),
            'currency_id': this.txContext.currencyId &&
                           parseInt(this.txContext.currencyId),
            'partner_id': parseInt(this.txContext.partnerId),
            'flow': 'direct',
            'tokenization_requested': false,
            'landing_route': this.txContext.landingRoute,
            'access_token': this.txContext.accessToken,
            'csrf_token': core.csrf_token,
        };
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
            const $submitButton = this.$('button[name="o_payment_submit_button"]');
            const iconClass = $submitButton.data('icon-class');
            $submitButton.attr('disabled', false);
            $submitButton.find('i').addClass(iconClass);
            $submitButton.find('span.o_loader').remove();
            return true;
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
     * Update the amount of the express checkout form.
     *
     * For a provider to manage an express form, it must override this method.
     *
     * @private
     * @param {number} newAmount - The new amount.
     * @param {number} newMinorAmount - The new minor amount.
     * @return {undefined}
     */
    _updateAmount(newAmount, newMinorAmount) {
        this.txContext.amount = parseFloat(newAmount);
        this.txContext.minorAmount = parseInt(newMinorAmount);
    },

});

export const paymentExpressCheckoutForm = publicWidget.registry.PaymentExpressCheckoutForm;
