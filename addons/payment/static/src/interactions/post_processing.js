import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

export class PaymentPostProcessing extends Interaction {
    static selector = "div[name='o_payment_status']";

    setup() {
        // Create a bus listener to trigger post-processing
        this.notificationType = "payment.notify_transaction_processed";
        this.notificationChannel = this.el.dataset.notificationChannel;
        this.onProcessingCompleteBind = this.onProcessingComplete.bind(this);
        this.busService = this.services.bus_service;
        this.busService.addChannel(this.notificationChannel);
        this.busService.subscribe(this.notificationType, this.onProcessingCompleteBind);

        // Redirect automatically after 5 seconds
        this.redirectTimeout = this.waitForTimeout(() => {
            this.redirectToLandingPage();
        }, 5000);
    }

    async willStart() {
        // Assume we missed a notification from the postprocessing
        await this.onProcessingComplete();
    }

    /**
     * Run the post-processing and redirect the user as soon a final state is reached.
     *
     * @returns {Promise<void>}
     */
    async onProcessingComplete() {
        const postProcessingData = await rpc(
            "/payment/post_process", { csrf_token: odoo.csrf_token }
        );
        const { provider_code, state } = postProcessingData;
        if (PaymentPostProcessing.getFinalStates(provider_code).has(state)) {
            this.redirectToLandingPage();
        }
    }

    /**
     * Clean up bus subscriptions and the timer and redirect to the landing route.
     */
    redirectToLandingPage() {
        // Cleanup before leaving the page, make sure bus listener is disposed properly on redirect.
        clearTimeout(this.redirectTimeout);
        this.busService.unsubscribe(this.notificationType, this.onProcessingCompleteBind);
        this.busService.deleteChannel(this.notificationChannel);

        // Redirect the user to the landing route
        window.location = this.el.dataset.landingRoute;
    }

    static getFinalStates(providerCode) {
        return new Set(['authorized', 'done', 'cancel', 'error']);
    }
}

registry
    .category("public.interactions")
    .add("payment.payment_post_processing", PaymentPostProcessing);
