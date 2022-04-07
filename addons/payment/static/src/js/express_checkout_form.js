/** @odoo-module */

import core from 'web.core';
import publicWidget from 'web.public.widget';

publicWidget.registry.PaymentExpressCheckoutForm = publicWidget.Widget.extend({
    selector: 'form[name="o_payment_express_checkout_form"]',

    /**
     * @override
     */
    start: async function () {
        await this._super(...arguments);
        this.txContext = {};
        Object.assign(this.txContext, this.$el.data());
        const expressCheckoutForms = this._getExpressCheckoutForms();
        for (const expressCheckoutForm of expressCheckoutForms) {
            await this._prepareExpressCheckoutForm(expressCheckoutForm.dataset);
        }
        // Monitor updates of the amount on eCommerce's cart pages.
        core.bus.on('cart_amount_changed', this, this._updateAllAmounts.bind(this));
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
     * Return whether the shipping information is required or not.
     *
     * For a module to request shipping information to the customer, it must override this method.
     *
     * @private
     * @return {Boolean} - Whether the shipping information is required or not.
     */
    _isShippingInformationRequired: () => false,

    /**
     * Prepare the acquirer-specific express checkout form based on the provided data.
     *
     * For an acquirer to manage an express checkout form, it must override this method.
     *
     * @private
     * @param {Object} acquirerData - The acquirer-specific data.
     * @return {Promise}
     */
    async _prepareExpressCheckoutForm(acquirerData) {
        return Promise.resolve();
    },

    /**
     * Prepare the params to send to the transaction route.
     *
     * For an acquirer to overwrite generic params or to add acquirer-specific ones, it must
     * override this method and return the extended transaction route params.
     *
     * @private
     * @param {number} acquirerId - The id of the acquirer handling the transaction.
     * @returns {object} - The transaction route params
     */
    _prepareTransactionRouteParams(acquirerId) {
        return {
            'payment_option_id': parseInt(acquirerId),
            'reference_prefix': this.txContext.referencePrefix &&
                                this.txContent.referencePrefix.toString(),
            'currency_id': this.txContext.currencyId &&
                           parseInt(this.txContext.currencyId),
            'partner_id': parseInt(this.txContext.partnerId),
            'flow': 'direct',
            'tokenization_requested': false,
            'landing_route': this.txContext.landingRoute,
            'add_id_to_landing_route': true,
            'access_token': this.txContext.accessToken,
            'csrf_token': core.csrf_token,
        };
    },

    /**
     * Retrieve all the express checkout forms and update the amount in each form.
     *
     * Note: triggered by bus event `cart_amount_changed`.
     *
     * @private
     * @param {number} newAmount - The new amount.
     * @param {number} newMinorAmount - The new minor amount.
     * @return {undefined}
     */
    _updateAllAmounts(newAmount, newMinorAmount) {
        const expressCheckoutForms = this._getExpressCheckoutForms();
        for (const expressCheckoutForm of expressCheckoutForms) {
            this._updateAmount(expressCheckoutForm.dataset, newAmount, newMinorAmount);
        }
    },

    /**
     * Update the amount of the express checkout form.
     *
     * For an acquirer to manage an express form, it must override this method.
     *
     * @private
     * @param {Object} acquirerData - The acquirer-specific data.
     * @param {number} newAmount - The new amount.
     * @param {number} newMinorAmount - The new minor amount.
     * @return {undefined}
     */
    _updateAmount(acquirerData, newAmount, newMinorAmount) {},

});

export const paymentExpressCheckoutForm = publicWidget.registry.PaymentExpressCheckoutForm;
