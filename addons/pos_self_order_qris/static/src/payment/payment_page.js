import { PaymentPage } from "@pos_self_order/app/pages/payment_page/payment_page";
import { isKioskQris, PaymentQris } from "./payment_qris";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { onWillUnmount } from "@odoo/owl";

const { Duration } = luxon;

patch(PaymentPage.prototype, {
    setup() {
        super.setup(...arguments);
        this.state.qrCountdown = null;
        this._qrTimerHandle = null;
        this._qrisPayment = null;
        onWillUnmount(() => this._stopQrPayment());
    },

    get showQrCode() {
        if (isKioskQris(this.selectedPaymentMethod)) {
            return !!this.state.qrCode;
        }
        return super.showQrCode;
    },

    async startPayment() {
        const paymentMethod = this.selectedPaymentMethod;
        if (!isKioskQris(paymentMethod)) {
            await super.startPayment(...arguments);
            return;
        }

        this.state.qrCode = null;
        this.state.paymentCancelled = false;
        this.selfOrder.paymentError = false;
        this._stopQrPayment();

        const order = await this.selfOrder.sendDraftOrderToServer();
        if (!order) {
            this.selfOrder.paymentError = true;
            return;
        }

        const payment = new PaymentQris(this.selfOrder, paymentMethod, order);
        try {
            this.state.qrCode = await payment.createQrCode();
        } catch (error) {
            this.selfOrder.handleErrorNotification(error);
            this.selfOrder.paymentError = true;
            return;
        }

        if (!this.state.qrCode) {
            // A QR handed out earlier was paid after all: the order is settled and the
            // confirmation page comes from the bus, so there is nothing to watch.
            return;
        }

        this._qrisPayment = payment;
        payment.watch((error) => this._onQrPaymentFailed(error));
        this._startQrTimer(payment.deadline);
    },

    _onQrPaymentFailed(error) {
        // The acquirer keeps the QR payable long after the kiosk stops waiting for it,
        // so take it off screen instead of leaving a code we no longer honour scannable.
        this.state.qrCode = null;
        this._stopQrPayment();
        this.selfOrder.paymentError = true;
        // Retry is the only safe way out: it checks the QRs handed out so far before
        // issuing a new one, so a customer who did pay is not asked to pay again.
        this.selfOrder.notification.add(
            _t("If you have already paid, tap Retry and we will check your payment again."),
            {
                title: error,
                type: "danger",
            }
        );
    },

    _stopQrPayment() {
        this._qrisPayment?.stop();
        this._qrisPayment = null;
        this._stopQrTimer();
    },

    get formattedQrCountdown() {
        return Duration.fromObject({ seconds: this.state.qrCountdown }).toFormat("m:ss");
    },

    _startQrTimer(deadline) {
        this._stopQrTimer();
        if (!deadline) {
            return;
        }
        const tick = () => {
            const remaining = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
            this.state.qrCountdown = remaining;
            if (remaining <= 0) {
                clearInterval(this._qrTimerHandle);
                this._qrTimerHandle = null;
            }
        };
        tick();
        this._qrTimerHandle = setInterval(tick, 1000);
    },

    _stopQrTimer() {
        if (this._qrTimerHandle) {
            clearInterval(this._qrTimerHandle);
            this._qrTimerHandle = null;
        }
        this.state.qrCountdown = null;
    },
});
