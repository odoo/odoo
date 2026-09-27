import { generateQRCodeDataUrl } from "@point_of_sale/utils";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";

const QRIS_FALLBACK_TIMEOUT = 180_000;
const QRIS_POLL_INTERVAL = 3000;
const QRIS_QR_SIZE = { width: 400, height: 400 };

export function isKioskQris(paymentMethod) {
    return (
        paymentMethod?.payment_method_type === "bank_qr_code" &&
        paymentMethod?.qr_code_method === "id_qr"
    );
}

export class PaymentQris {
    /**
     * @param {Object} selfOrder - the `SelfOrder` service
     * @param {Object} paymentMethod - the `pos.payment.method` being paid with
     * @param {Object} order - the `pos.order` being paid, already sent to the server
     */
    constructor(selfOrder, paymentMethod, order) {
        this.selfOrder = selfOrder;
        this.paymentMethod = paymentMethod;
        this.order = order;
        this.deadline = null;
        this._pollHandle = null;
        this._watching = false;
        this._onFailure = null;
    }

    /**
     * Ask the acquirer for a QR and note the deadline it has to be paid by.
     *
     * @return {string|null} the QR as a data URL, ready to be displayed, or `null` if a
     *      QR issued earlier turned out to be paid: the server has settled the order and
     *      pushed the confirmation over the bus, there is nothing left to display.
     */
    async createQrCode() {
        const { paid, qr_content, expires_in } = await this._call("kiosk_qr_create_payment");
        if (paid) {
            return null;
        }
        this.deadline =
            Date.now() + (expires_in === undefined ? QRIS_FALLBACK_TIMEOUT : expires_in * 1000);
        return generateQRCodeDataUrl(qr_content, QRIS_QR_SIZE);
    }

    /**
     * Poll the acquirer until the payment is settled. A payment that goes through is
     * confirmed by the server over the bus, so only the failures are reported back here.
     *
     * @param {function(string): void} onFailure - called with the reason the payment
     *      will not complete
     */
    watch(onFailure) {
        this.stop();
        this._onFailure = onFailure;
        this._watching = true;
        this._schedulePoll();
    }

    stop() {
        if (this._pollHandle) {
            clearTimeout(this._pollHandle);
        }
        this._pollHandle = null;
        this._watching = false;
    }

    _schedulePoll() {
        this._pollHandle = setTimeout(() => this._poll(), QRIS_POLL_INTERVAL);
    }

    async _poll() {
        this._pollHandle = null;
        if (!this._watching) {
            return; // stopped while the timer was pending
        }

        if (Date.now() > this.deadline) {
            this._fail(_t("Payment timed out"));
            return;
        }

        let status;
        try {
            ({ status } = await this._call("kiosk_qr_poll_payment"));
        } catch {
            if (this._watching) {
                this._schedulePoll();
            }
            return;
        }

        if (!this._watching) {
            return; // stopped while the call was in flight
        }
        if (status === "pending") {
            this._schedulePoll();
            return;
        }
        if (status === "paid") {
            this.stop();
            return;
        }
        this._fail(_t("Payment expired"));
    }

    _fail(error) {
        this.stop();
        this._onFailure?.(error);
    }

    async _call(action) {
        return await rpc(
            `/kiosk/payment_method_action/${action}`,
            {
                access_token: this.selfOrder.access_token,
                args: [[this.paymentMethod.id], this.order.uuid],
                kwargs: {},
            },
            { silent: true }
        );
    }
}
