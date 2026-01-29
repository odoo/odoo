/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';
import { renderToElement } from '@web/core/utils/render';
import { markup } from "@odoo/owl";
import { formatCurrency } from "@web/core/currency";
import { _t } from '@web/core/l10n/translation';
import { ConnectionLostError, RPCError } from '@web/core/network/rpc_service';

publicWidget.registry.PaymentPostProcessing = publicWidget.Widget.extend({
    selector: 'div[name="o_payment_status"]',

    timeout: 0,
    pollCount: 0,

    init() {
        this._super(...arguments);
        this.rpc = this.bindService("rpc");
    },

    async start() {
        this.call('ui', 'block', {
            'message': _t("We are processing your payment. Please wait."),
        });
        this._poll();
        return this._super.apply(this, arguments);
    },

    _poll() {
        this._updateTimeout();
        setTimeout(() => {
            // Fetch the post-processing values from the server.
            const self = this;
            this.rpc('/payment/status/poll', {
                'csrf_token': odoo.csrf_token,
            }).then(postProcessingValues => {
                let { state, display_message, landing_route } = postProcessingValues;

                // Display the transaction details before redirection to show something ASAP.
                if (display_message) {
                    postProcessingValues.display_message = markup(display_message);
                }
                this._renderTemplate(
                    'payment.transactionDetails', {...postProcessingValues, formatCurrency}
                );

                // Redirect the user to the landing route if the transaction reached a final state.
                if (self._getFinalStates(postProcessingValues['provider_code']).includes(state)) {
                    window.location = landing_route;
                } else {
                    self._poll();
                }
            }).catch(error => {
                if (error instanceof RPCError) { // Server error.
                    switch (error.data.message) {
                        case 'retry':
                            self._poll();
                            break;
                        case 'tx_not_found':
                            self._renderTemplate('payment.tx_not_found');
                            break;
                        default:
                            self._renderTemplate(
                                'payment.exception', { error_message: error.data.message }
                            );
                            break;
                    }
                } else if (error instanceof ConnectionLostError) { // RPC error (server unreachable).
                    self._renderTemplate('payment.rpc_error');
                    self._poll();
                } else {
                    return Promise.reject(error);
                }
            });
        }, this.timeout);
    },

    _getFinalStates(providerCode) {
        return ['authorized', 'done'];
    },

    _updateTimeout() {
        if (this.pollCount >= 1 && this.pollCount < 10) {
            this.timeout = 3000;
        }
        if (this.pollCount >= 10 && this.pollCount < 20) {
            this.timeout = 10000;
        }
        else if (this.pollCount >= 20) {
            this.timeout = 30000;
        }
        this.pollCount++;
    },

    _renderTemplate(xmlid, display_values={}) {
        this.call('ui', 'unblock');
        const statusContainer = document.querySelector('div[name="o_payment_status_content"]');
        statusContainer.innerHTML = renderToElement(xmlid, display_values).innerHTML;
    },

});

export default publicWidget.registry.PaymentPostProcessing;
