import { PaymentPage } from "@pos_self_order/app/pages/payment_page/payment_page";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { onWillUnmount } from "@odoo/owl";

const { Duration } = luxon;

patch(PaymentPage.prototype, {
    setup() {
        super.setup(...arguments);
        this.state.qrCountdown = null;
        this._qrTimerHandle = null;
        onWillUnmount(() => this._stopQrTimer());
    },

    async processElectronicPayment() {
        try {
            return await super.processElectronicPayment(...arguments);
        } catch (error) {
            if (this._qrTimerHandle) {
                this._stopQrTimer();
                this.selfOrder.notification.add(
                    _t("If you have already paid, tap Retry and we will check your payment again."),
                    {
                        title: error,
                        type: "danger",
                    }
                );
                this.selfOrder.paymentError = true;
            } else {
                throw error;
            }
        }
    },

    handleStartPaymentResult(result) {
        super.handleStartPaymentResult(...arguments);
        if (result.expires_in) {
            this._startQrTimer(Date.now() + result.expires_in * 1000);
        }
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
        };
        tick();
        this._qrTimerHandle = setInterval(tick, 1000);
    },

    _stopQrTimer() {
        if (this._qrTimerHandle) {
            clearInterval(this._qrTimerHandle);
            this._qrTimerHandle = null;
            this.state.qrCode = null;
        }
        this.state.qrCountdown = null;
    },
});
