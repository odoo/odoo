import { registry } from '@web/core/registry';
import { Interaction } from '@web/public/interaction';

export class ExpressCheckout extends Interaction {
    static selector = 'form[name="o_payment_express_checkout_form"]';

    setup() {
        this.paymentContext = {};
        Object.assign(this.paymentContext, this.el.dataset);
        this.paymentContext.shippingInfoRequired = !!this.paymentContext.shippingInfoRequired;
    }

    async willStart() {
        const expressCheckoutForm = this._getExpressCheckoutForm();
        if (expressCheckoutForm) {
            await this._prepareExpressCheckoutForm(expressCheckoutForm.dataset);
        }
    }

    start() {
        // Monitor updates of the amount on eCommerce's cart pages.
        this.env.bus.addEventListener('cart_amount_changed', (ev) =>
            this._updateAmount(...ev.detail)
        );
        // Monitor when the page is restored from the bfcache.
        this.addListener(window, 'pageshow', this._onNavigationBack);
    }

    /**
     * Reload the page when the page is restored from the bfcache.
     *
     * @param {PageTransitionEvent} event - The pageshow event.
     * @private
     */
    _onNavigationBack(event) {
        if (event.persisted) {
            window.location.reload();
        }
    }

    /**
     * Return the express checkout form, if found.
     *
     * @private
     * @return {Element|null} - The express checkout form.
     */
    _getExpressCheckoutForm() {
        return document.querySelector(
            'form[name="o_payment_express_checkout_form"] div[name="o_express_checkout_container"]'
        );
    }

    /**
     * Prepare the provider-specific express checkout form based on the provided data.
     *
     * For a provider to manage an express checkout form, it must override this method.
     *
     * @private
     * @param {Object} providerData - The provider-specific data.
     * @return {void}
     */
    async _prepareExpressCheckoutForm(providerData) {}

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
    }

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
        this._getExpressCheckoutForm()?.classList?.toggle(
            'd-none', this.paymentContext.amount === 0
        );
    }
}

registry
    .category('public.interactions')
    .add('payment.express_checkout', ExpressCheckout);
