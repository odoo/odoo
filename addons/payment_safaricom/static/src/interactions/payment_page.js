import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { redirect } from "@web/core/utils/urls";
import { Interaction } from "@web/public/interaction";

const PAYMENT_STATUS_URL = "/payment/status";

export class SafaricomPayPage extends Interaction {
    static selector = "div[name='o_safaricom_pay']";
    dynamicContent = {
        "a[name='o_safaricom_skip']": {
            "t-att-class": () => ({ "d-none": !this.showSkipButton }),
            "t-on-click": (ev) => {
                ev.preventDefault();
                this.exitTo(this.el.dataset.landingRoute);
            },
        },
        "a[name='o_safaricom_cancel']": {
            "t-on-click": this.locked(this.onCancel, true),
        },
    };

    setup() {
        this.notificationType = "payment_safaricom.callback_received";
        this.notificationChannel = this.el.dataset.notificationChannel;
        this.onCallbackReceivedBind = this.onCallbackReceived.bind(this);
        this.busService = this.services.bus_service;
        this.busService.addChannel(this.notificationChannel);
        this.busService.subscribe(this.notificationType, this.onCallbackReceivedBind);

        this.showSkipButton = false;
        this.waitForTimeout(() => this.showSkipButton = true, 30000);
        this.waitForTimeout(() => this.exitTo(PAYMENT_STATUS_URL), 120000);
    }

    /**
     * Leave for the status page, whose processing call finalizes the transaction.
     *
     * @returns {void}
     */
    onCallbackReceived() {
        this.exitTo(PAYMENT_STATUS_URL);
    }

    /**
     * Cancel the transaction and leave for the status page.
     *
     * @param {Event} ev
     * @returns {Promise<void>}
     */
    async onCancel(ev) {
        ev.preventDefault();
        await this.waitFor(rpc("/payment/safaricom/cancel"));
        this.exitTo(PAYMENT_STATUS_URL);
    }

    /**
     * Clean up the bus subscription and redirect to the given route.
     *
     * @param {string} route - The route to be redirected to.
     * @returns {void}
     */
    exitTo(route) {
        this.busService.unsubscribe(this.notificationType, this.onCallbackReceivedBind);
        this.busService.deleteChannel(this.notificationChannel);
        redirect(route);
    }
}

registry
    .category("public.interactions")
    .add("payment_safaricom.pay_page", SafaricomPayPage);
