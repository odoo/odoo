import { ConnectionLostError, rpc, RPCError } from '@web/core/network/rpc';
import { registry } from '@web/core/registry';
import { Interaction } from '@web/public/interaction';

export class PaymentPostProcessing extends Interaction {
    static selector = 'div[name="o_payment_status"]';

    setup() {
        this.timeout = 0;
        this.pollCount = 0;
    }

    start() {
        this.poll();
    }

    poll() {
        this.updateTimeout();
        this.waitForTimeout(async () => {
            try {
                // Fetch the post-processing values from the server.
                const postProcessingValues = await this.waitFor(
                    rpc('/payment/status/poll', { csrf_token: odoo.csrf_token })
                );

                // Redirect the user to the landing route if the transaction reached a final state.
                const { provider_code, state, landing_route } = postProcessingValues;
                if (PaymentPostProcessing.getFinalStates(provider_code).has(state)) {
                    window.location = landing_route;
                } else {
                    this.poll();
                }
            } catch (error) {
                const isRetryError = error instanceof RPCError && error.data.message === 'retry';
                const isConnectionLostError = error instanceof ConnectionLostError;
                if (isRetryError || isConnectionLostError) {
                    this.poll();
                }
                if (!isRetryError) {
                    throw error;
                }
            }
        }, this.timeout);
    }

    static getFinalStates(providerCode) {
        return new Set(['authorized', 'done', 'cancel', 'error']);
    }

    updateTimeout() {
        if (this.pollCount >= 1 && this.pollCount < 10) {
            this.timeout = 3000;
        }
        if (this.pollCount >= 10 && this.pollCount < 20) {
            this.timeout = 10000;
        } else if (this.pollCount >= 20) {
            this.timeout = 30000;
        }
        this.pollCount++;
    }
}

registry
    .category('public.interactions')
    .add('payment.payment_post_processing', PaymentPostProcessing);
