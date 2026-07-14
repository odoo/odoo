import { rpc } from "@web/core/network/rpc";
import { redirect } from "@web/core/utils/urls";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

export class PaymentStatus extends Interaction {
    static selector = "div[name='o_payment_status']";

    setup() {
        // Create a bus listener to be notified when the transaction processing is complete
        this.notificationType = "payment.transaction_status";
        this.notificationChannel = this.el.dataset.notificationChannel;
        this.onProcessingCompleteBind = this.onProcessingComplete.bind(this);
        this.busService = this.services.bus_service;
        this.busService.addChannel(this.notificationChannel);
        this.busService.subscribe(this.notificationType, this.onProcessingCompleteBind);

        // Redirect automatically after 10 seconds in case the channel subscription fails
        this.redirectTimeout = this.waitForTimeout(() => {
            this.redirectToLandingPage(this.el.dataset.landingRoute);
        }, 10000);
    }

    async willStart() {
        // Trigger immediate processing instead of waiting for the next triggered cron run
        await rpc("/payment/process");
    }

    /**
     * Redirect the user to the landing route when a final state is reached.
     *
     * @param {Object} statusData - The status values of the transaction
     * @returns {void}
     */
    onProcessingComplete(statusData) {
        const { reference, provider_code, state, landing_route } = statusData;
        if (reference !== this.el.dataset.transactionReference) {  // Old notification replay
            return;  // Ignore notifications for other transactions than the one being monitored
        }
        if (PaymentStatus.getFinalStates(provider_code).has(state)) {
            this.redirectToLandingPage(landing_route);
        }
    }

    /**
     * Clean up bus subscriptions and the timer and redirect to the landing route.
     *
     * @param {string} landingRoute - The landing route to be redirected to
     * @returns {void}
     */
    redirectToLandingPage(landingRoute) {
        // Cleanup before leaving the page; make sure bus listener is disposed properly on redirect
        clearTimeout(this.redirectTimeout);
        this.busService.unsubscribe(this.notificationType, this.onProcessingCompleteBind);
        this.busService.deleteChannel(this.notificationChannel);

        // Redirect the user to the landing route
        redirect(landingRoute);
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
}

registry.category("public.interactions").add("payment.payment_status", PaymentStatus);
