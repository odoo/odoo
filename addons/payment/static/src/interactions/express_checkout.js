import { ConfirmationDialog } from '@web/core/confirmation_dialog/confirmation_dialog';
import { _t } from '@web/core/l10n/translation';
import { rpc, RPCError } from '@web/core/network/rpc';
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
            const providerData = expressCheckoutForm.dataset;
            this._updatePaymentContext(providerData);
            await this._prepareExpressCheckoutForm(providerData);
        }
    }

    start() {
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
        let processingValues = {};
        try {
            // Create a transaction and retrieve its processing values.
            processingValues = await this.waitFor(rpc(
                this.paymentContext['transactionRoute'],
                this._prepareTransactionRouteParams(),
            ));
        } catch (error) {
            if (error instanceof RPCError) {
                processingValues = {state: 'error', state_message: error.data.message};
            }
        }

        if (processingValues.state === 'error') {
            this._handlePaymentProcessingError(processingValues);
        }
        return processingValues;
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
     * Handle the processing values if the transaction creation failed by displaying a dialog.
     *
     * @param {Object} processingValues - The response values returned at the transaction creation
     * @param {string} processingValues.state_message - The error message to display to the user
     */
    _handlePaymentProcessingError(processingValues) {
        this._displayErrorDialog(_t("Payment processing failed"), processingValues.state_message);
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
