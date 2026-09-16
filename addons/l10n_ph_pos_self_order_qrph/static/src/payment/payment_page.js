import { PaymentPage } from "@pos_self_order/app/pages/payment_page/payment_page";
import { isKioskQrph, PaymentQrph } from "./payment_qrph";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { onWillUnmount } from "@odoo/owl";

const { Duration } = luxon;

// How long the customer is given to scan again after telling us they have already paid.
const QRPH_COUNTDOWN_MS = 180_000;

patch(PaymentPage.prototype, {
    setup() {
        super.setup(...arguments);
        this.state.qrphCountdown = null;
        this.state.qrphChecking = false;
        this._qrphTimerHandle = null;
        this._qrphPayment = null;
        onWillUnmount(() => this._stopQrphTimer());
    },

    get isKioskQrph() {
        return isKioskQrph(this.selectedPaymentMethod);
    },

    get showQrCode() {
        if (this.isKioskQrph) {
            return !!this.state.qrCode;
        }
        return super.showQrCode;
    },

    get formattedQrphCountdown() {
        return Duration.fromObject({ seconds: this.state.qrphCountdown }).toFormat("m:ss");
    },

    async startPayment() {
        const paymentMethod = this.selectedPaymentMethod;
        if (!isKioskQrph(paymentMethod)) {
            await super.startPayment(...arguments);
            return;
        }

        this.state.qrCode = null;
        this.state.paymentCancelled = false;
        this.selfOrder.paymentError = false;
        this._stopQrphTimer();

        // The code is minted against the order, so the order has to exist before asking for one.
        const order = await this.selfOrder.sendDraftOrderToServer();
        if (!order) {
            this.selfOrder.paymentError = true;
            return;
        }

        const payment = new PaymentQrph(this.selfOrder, paymentMethod, order);
        try {
            this.state.qrCode = await payment.createQrCode();
        } catch (error) {
            this.selfOrder.handleErrorNotification(error);
            this.selfOrder.paymentError = true;
            return;
        }

        if (!this.state.qrCode) {
            // A code handed out earlier was paid after all: the order is settled and its
            // confirmation comes over the bus, so there is nothing left to put on screen.
            return;
        }

        this._qrphPayment = payment;
        this._startQrphTimer(payment.deadline);
    },

    /**
     * Have the server check with Maya, for the customer who paid and is still looking at the code.
     *
     * Maya notifies the server on its own, and that is what normally takes the kiosk to the
     * receipt. This covers the notification that is late, lost, or was never configured.
     */
    async checkQrphPayment() {
        if (this.state.qrphChecking || !this._qrphPayment) {
            return;
        }
        this.state.qrphChecking = true;
        try {
            if (await this._qrphPayment.verify()) {
                // The order is settled, and the bus takes it from here.
                return;
            }
            this.selfOrder.notification.add(
                _t("Scan the code with your banking application, and we will check again."),
                { title: _t("No payment received yet"), type: "warning" }
            );
            // Maya honours the code well past the countdown, so the customer keeps the one on
            // screen and is given the time to pay it rather than a second code to scan.
            this._qrphPayment.deadline = Date.now() + QRPH_COUNTDOWN_MS;
            this._startQrphTimer(this._qrphPayment.deadline);
        } catch (error) {
            this.selfOrder.handleErrorNotification(error);
        } finally {
            this.state.qrphChecking = false;
        }
    },

    _startQrphTimer(deadline) {
        this._stopQrphTimer();
        if (!deadline) {
            return;
        }
        const tick = () => {
            const remaining = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
            this.state.qrphCountdown = remaining;
            if (remaining <= 0) {
                clearInterval(this._qrphTimerHandle);
                this._qrphTimerHandle = null;
            }
        };
        tick();
        this._qrphTimerHandle = setInterval(tick, 1000);
    },

    _stopQrphTimer() {
        if (this._qrphTimerHandle) {
            clearInterval(this._qrphTimerHandle);
            this._qrphTimerHandle = null;
        }
        this.state.qrphCountdown = null;
    },
});
