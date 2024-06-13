/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';
import { ConnectionLostError, rpc, RPCError } from '@web/core/network/rpc';

publicWidget.registry.PaymentPostProcessing = publicWidget.Widget.extend({
    selector: 'div[name="o_payment_status"]',

    timeout: 0,
    pollCount: 0,

    async start() {
        this._poll();
        return this._super.apply(this, arguments);
    },

    _poll() {
        this._updateTimeout();
        setTimeout(() => {
            // Fetch the post-processing values from the server.
            const self = this;
            rpc('/payment/status/poll', {
                'csrf_token': odoo.csrf_token,
            }).then(postProcessingValues => {
                let {provider_code, state, landing_route} = postProcessingValues;

                // Redirect the user to the landing route if the transaction reached a final state.
                if (self._getFinalStates(provider_code).has(state)) {
                    window.location = landing_route;
                } else {
                    self._poll();
                }
            }).catch(error => {
                const isRetryError = error instanceof RPCError && error.data.message === 'retry';
                const isConnectionLostError = error instanceof ConnectionLostError;
                if (isRetryError || isConnectionLostError) {
                    self._poll();
                }
                if (!isRetryError) {
                    throw error;
                }
            });
        }, this.timeout);
    },

    _getFinalStates(providerCode) {
        return new Set(['authorized', 'done', 'cancel', 'error']);
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
});

export default publicWidget.registry.PaymentPostProcessing;
