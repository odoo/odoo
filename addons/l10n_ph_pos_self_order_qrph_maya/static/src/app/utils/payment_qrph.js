import { generateQRCodeDataUrl } from "@point_of_sale/utils";
import { rpc } from "@web/core/network/rpc";

// Used when the server does not say how long the customer has, so the kiosk still counts down.
const QRPH_FALLBACK_TIMEOUT = 180;
const QRPH_QR_METHOD = "ph_qrph_maya";
const QRPH_QR_SIZE = { width: 400, height: 400 };

export function isKioskQrph(paymentMethod) {
    return (
        paymentMethod?.payment_method_type === "bank_qr_code" &&
        paymentMethod?.qr_code_method === QRPH_QR_METHOD
    );
}

export class PaymentQrph {
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
        // What Maya received for the order when it was not enough to pay it, to tell the customer.
        this.shortPayment = null;
    }

    /**
     * Ask Maya for a code and note how long the kiosk gives the customer to scan it.
     *
     * Nothing is polled afterwards: Maya does not tell us when the code is paid, so the customer
     * asks for a check with `verify`, and the server settles the order and pushes the
     * confirmation over the bus.
     *
     * @return {string|null} the code as a data URL, ready to be displayed, or `null` if a code
     *      handed out earlier turned out to be paid, leaving nothing left to show.
     */
    async createQrCode() {
        const { paid, qr_content, expires_in, short_payment } = await this._call(
            "l10n_ph_kiosk_qrph_create_payment"
        );
        if (paid) {
            return null;
        }
        this.shortPayment = short_payment || null;
        this.deadline = Date.now() + (expires_in ?? QRPH_FALLBACK_TIMEOUT) * 1000;
        return generateQRCodeDataUrl(qr_content, QRPH_QR_SIZE);
    }

    /**
     * Have the server ask Maya about the codes issued for this order.
     *
     * This is what takes the customer who has paid from the code to the receipt.
     *
     * @return {boolean} whether the order came out of it paid
     */
    async verify() {
        const { paid, short_payment } = await this._call("l10n_ph_kiosk_qrph_verify_payment");
        this.shortPayment = short_payment || null;
        return paid;
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
