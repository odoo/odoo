import { browser } from '@web/core/browser/browser';
import { patch } from '@web/core/utils/patch';
import { rpc } from '@web/core/network/rpc';

import { PaymentStatus } from '@payment/interactions/payment_status';

patch(PaymentStatus.prototype, {
    /**
     * Set up the Safaricom controls: start the processing poll and reveal the cancel link once the
     * initial processing is done (see `willStart`) and the skip link after a delay.
     *
     * @override method from `@payment/interactions/payment_status`
     */
    setup() {
        super.setup(...arguments);
        if (this.el.dataset.providerCode !== 'safaricom') {
            return;
        }
        this.showSkipButton = false;
        this.showCancelButton = false;
        this.waitForTimeout(() => this.showSkipButton = true, 30000);
        this.dynamicContent = {
            "a[name='o_safaricom_skip']": {
                "t-att-class": () => ({ "d-none": !this.showSkipButton }),
                "t-on-click": (ev) => {
                    ev.preventDefault();
                    this.redirectToLandingPage();
                },
            },
            "a[name='o_safaricom_cancel']": {
                "t-att-class": () => ({ "d-none": !this.showCancelButton }),
                "t-on-click": this.locked(this.onSafaricomCancel, true),
            },
        };
        this._safaricomScheduleProcessingPoll();
    },

    /**
     * Poll for a final transaction state as a fallback for the redirect-triggering bus
     * notification. For M-PESA the transaction is still pending at page load, so notification is
     * the only redirect trigger and is easily missed or delayed.
     */
    _safaricomScheduleProcessingPoll() {
        this.safaricomPollTimeout = this.waitForTimeout(async () => {
            await this.waitFor(rpc('/payment/process'));
            await this.onProcessingComplete();
            this._safaricomScheduleProcessingPoll();
        }, 3000);
    },

    /**
     * Reveal the cancel link only after the initial processing is done. Until `willStart` resolves
     * the interaction is not started, so its handlers are unbound and a visible button would be
     * unresponsive.
     *
     * @override method from `@payment/interactions/payment_status`
     */
    async willStart() {
        await super.willStart(...arguments);
        if (this.el.dataset.providerCode === 'safaricom') {
            this.showCancelButton = true;
        }
    },

    /**
     * Override to stop the processing poll before leaving the page.
     *
     * @override method from `@payment/interactions/payment_status`
     */
    redirectToLandingPage() {
        browser.clearTimeout(this.safaricomPollTimeout);
        super.redirectToLandingPage(...arguments);
    },

    /**
     * Cancel the transaction.
     *
     * @param {Event} ev
     * @returns {Promise<void>}
     */
    async onSafaricomCancel(ev) {
        ev.preventDefault();
        await this.waitFor(rpc('/payment/safaricom/cancel'));
        await this.onProcessingComplete();
    },
});

patch(PaymentStatus, {
    /**
     * Wait for the customer to confirm the STK Push prompt on their phone before redirecting.
     *
     * @override method from `@payment/interactions/payment_status`
     * @param {string} providerCode - The code of the provider handling the transaction.
     */
    getRedirectTimeoutDelay(providerCode) {
        if (providerCode === 'safaricom') {
            return 120000; // The STK Push prompt expires unanswered after 2 minutes
        }
        return super.getRedirectTimeoutDelay(...arguments);
    },
});