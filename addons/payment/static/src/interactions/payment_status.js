import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

export class PaymentStatus extends Interaction {
    static selector = "div[name='o_payment_status']";

    setup() {
        // Create a bus listener to trigger post-processing
        this.notificationType = "payment.notify_transaction_processed";
        this.notificationChannel = this.el.dataset.notificationChannel;
        this.onProcessingCompleteBind = this.onProcessingComplete.bind(this);
        this.busService = this.services.bus_service;
        this.busService.addChannel(this.notificationChannel);
        this.busService.subscribe(this.notificationType, this.onProcessingCompleteBind);

        // Redirect automatically after a delay to avoid waiting for post-processing forever.
        this.redirectTimeout = this.waitForTimeout(() => {
            this.redirectToLandingPage();
        }, PaymentStatus.getRedirectTimeoutDelay(this.el.dataset.providerCode));
    }

    async willStart() {
        // Trigger immediate processing instead of waiting for the next scheduled cron run
        await rpc("/payment/process");

        // Trigger immediate post-processing as fallback for the case where the bus notification was
        // sent before we had time to subscribe to the channel
        await this.onProcessingComplete();
    }

    /**
     * Run the post-processing and wait for it to redirect the user when a final state is reached.
     *
     * @returns {Promise<void>}
     */
    async onProcessingComplete() {
        const postProcessingData = await rpc(
            "/payment/post_process", { csrf_token: odoo.csrf_token }
        );
        const { provider_code, state, is_post_processed, landing_route } = postProcessingData;
        if (is_post_processed && PaymentStatus.getFinalStates(provider_code).has(state)) {
            this.redirectToLandingPage(landing_route);
        }
    }

    /**
     * Clean up bus subscriptions and the timer and redirect to the landing route.
     *
     * @param {string} [landingRoute] - The up-to-date landing route; the one rendered on the page
     *                                  may be outdated if the transaction was updated since then.
     * @returns {void}
     */
    redirectToLandingPage(landingRoute) {
        // Cleanup before leaving the page, make sure bus listener is disposed properly on redirect.
        clearTimeout(this.redirectTimeout);
        this.busService.unsubscribe(this.notificationType, this.onProcessingCompleteBind);
        this.busService.deleteChannel(this.notificationChannel);

        // Redirect the user to the landing route
        const url = new URL(landingRoute || this.el.dataset.landingRoute, window.location.origin);
        window.location = url.origin === window.location.origin
            ? url.pathname + url.search + url.hash
            : "/";
    }

    /**
     * Returns the set of transaction's final states.
     *
     * @param {string} providerCode - The payment provider code.
     * @returns {Set<string>} - Set of transaction's final states.
     */
    static getFinalStates(providerCode) {
        return new Set(["authorized", "done", "cancel", "error"]);
    }

    /**
     * Returns the delay after which customers are redirected to the landing route, even if the
     * transaction has not reached a final state yet.
     *
     * @param {string} providerCode - The payment provider code.
     * @returns {number} - The redirect delay in milliseconds.
     */
    static getRedirectTimeoutDelay(providerCode) {
        return 10000;
    }
}

registry.category("public.interactions").add("payment.payment_status", PaymentStatus);
