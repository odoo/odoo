/** @odoo-module **/

import paymentForm from '@payment/js/payment_form';
import { jsonrpc, RPCError } from "@web/core/network/rpc_service";
import { _t } from "@web/core/l10n/translation";
import { PaymentMonerisDialog } from './moneris_dialog'


paymentForm.include({
    _processDirectFlow: function (providerCode, paymentOptionId, paymentMethodCode, processingValues) {
        if (providerCode !== 'moneris') {
            return this._super(...arguments);
        }
        var self = this;
        return jsonrpc('/payment/moneris/payment_details',{
                'code': providerCode,
                'provider_id': processingValues.provider_id,
                'amount': processingValues.amount,
                'currency_id': processingValues.currency_id,
                'partner_id': processingValues.partner_id,
                'reference': processingValues.reference,
            }).then((response) => {
                if (response && response.success == 'true'  && response.ticket) {
                    self.ticket = response.ticket
                    self.moneris_redirect_uri = response.redirect_uri
                    self.environment = response.environment
                    self.showMonerisDialog();
                } else if (response && response.success == 'false') {
                    console.log(response);
                    $('.btn-close').click();
                    this.call('ui', 'unblock');
                    self._displayErrorDialog(
                        _t("Moneris Error: "),
                        _t("We are not able to process your payment. \nMoneris Error Message: " + JSON.stringify(response.error_message))
                    )
                };
            }).catch((error) => {
                if (error instanceof RPCError) {
                    this._displayErrorDialog(_t("Payment processing failed"), error.data.message);
                    this._enableButton?.(); // This method doesn't exists in Express Checkout form.
                } else {
                    return Promise.reject(error);
                }
            });
        },

    _prepareInlineForm(providerId, providerCode, paymentOptionId, paymentMethodCode, flow) {
        if (providerCode !== 'moneris') {
            return this._super(...arguments);
        }
        if (flow === 'token') {
            return Promise.resolve();
        }
        this._setPaymentFlow('direct');
        return Promise.resolve()
    },

    async showMonerisDialog(ev) {
        var self = this;
        if (this.getParent() && this.getParent().env && this.getParent().env.services && this.getParent().env.services.ui.isBlocked){
            this.call('ui', 'unblock');
        };
        this.call("dialog", "add", PaymentMonerisDialog, {
            ticket:self.ticket,
            moneris_redirect_uri:self.moneris_redirect_uri,
            tokenizationRequested:self.paymentContext['tokenizationRequested'],
            env:self.environment,
        })
    },
});
