import { ConfirmationDialog } from '@web/core/confirmation_dialog/confirmation_dialog';
import { _t } from '@web/core/l10n/translation';
import { rpc, RPCError } from '@web/core/network/rpc';
import { registry } from '@web/core/registry';
import { redirect } from '@web/core/utils/urls';
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
        const providerData = expressCheckoutForm.dataset;
        this._updatePaymentContext(providerData)
        if (expressCheckoutForm) {
            await this._prepareExpressCheckoutForm(providerData);
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
     * Display an error dialog.
     *
     * @private
     * @param {string} title - The title of the dialog.
     * @param {string} errorMessage - The error message.
     * @return {void}
     */
    _displayErrorDialog(title, errorMessage = "") {
        this.services.dialog.add(ConfirmationDialog, { title: title, body: errorMessage || "" });
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

    _updatePaymentContext(providerData) {
        this.paymentContext.providerId = providerData.providerId;
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
     * Make an RPC to initiate the express payment flow by creating a new transaction.
     *
     * @private
     * @return {Object} - The transaction processing values.
     */
    async _prepareExpressTransaction() {
        try {
            // Create a transaction and retrieve its processing values.
            const processingValues = await this.waitFor(rpc(
                this.paymentContext['transactionRoute'],
                this._prepareTransactionRouteParams(),
            ));
            if (processingValues.state === 'error') {
                if (processingValues.redirect) {
                    redirect(processingValues.redirect);
                } else {
                    this._displayErrorDialog(
                        _t("Payment processing failed"), processingValues.state_message
                    );
                }
            }
            return processingValues;
        } catch (error) {
            if (error instanceof RPCError) {
                this._displayErrorDialog(_t("Payment processing failed"), error.data.message);
            }
            return {state: 'error', state_message: error.data.message};
        }
    }

    /**
     * Prepare the params for the RPC to the transaction route.
     *
     * @private
     * @returns {object} - The transaction route params.
     */
    _prepareTransactionRouteParams() {
        return {
            'provider_id': parseInt(this.paymentContext['providerId']),
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
