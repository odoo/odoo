/** @odoo-module */

import publicWidget from '@web/legacy/js/public/public_widget';
import { Component } from '@odoo/owl';

publicWidget.registry.PaymentExpressCheckoutForm = publicWidget.Widget.extend({
    selector: 'form[name="o_payment_express_checkout_form"]',

    /**
     * @override
     */
    start: async function () {
        await this._super(...arguments);
        this.paymentContext = {};
        Object.assign(this.paymentContext, this.el.dataset);
        this.paymentContext.shippingInfoRequired = !!this.paymentContext['shippingInfoRequired'];
        const expressCheckoutForms = this._getExpressCheckoutForms();
        for (const expressCheckoutForm of expressCheckoutForms) {
            await this._prepareExpressCheckoutForm(expressCheckoutForm.dataset);
        }
        // Monitor updates of the amount on eCommerce's cart pages.
        Component.env.bus.addEventListener('cart_amount_changed', (ev) => this._updateAmount(...ev.detail));
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
     * @return {void}
     */
    async _prepareExpressCheckoutForm(providerData) {},

    /**
     * Prepare the params for the RPC to the transaction route.
     *
     * @private
     * @param {number} providerId - The id of the provider handling the transaction.
     * @returns {object} - The transaction route params.
     */
    _prepareTransactionRouteParams(providerId) {
        return {
            'provider_id': parseInt(providerId),
            'payment_method_id': parseInt(this.paymentContext['paymentMethodUnknownId']),
            'token_id': null,
            'flow': 'direct',
            'tokenization_requested': false,
            'landing_route': this.paymentContext['landingRoute'],
            'access_token': this.paymentContext['accessToken'],
            'csrf_token': odoo.csrf_token,
        };
    },

    /**
     * Update the amount of the express checkout form.
     *
     * For a provider to manage an express form, it must override this method.
     *
     * @private
     * @param {number} newAmount - The new amount.
     * @param {number} newMinorAmount - The new minor amount.
     * @return {void}
     */
    _updateAmount(newAmount, newMinorAmount) {
        this.paymentContext.amount = parseFloat(newAmount);
        this.paymentContext.minorAmount = parseInt(newMinorAmount);
        this._getExpressCheckoutForms().forEach(form => {
            if (newAmount == 0) {
                form.classList.add('d-none')}
            else {
                form.classList.remove('d-none')
            }
        })
    },

});

export const paymentExpressCheckoutForm = publicWidget.registry.PaymentExpressCheckoutForm;
