import { patch } from "@web/core/utils/patch";
import { PosPaymentMethod } from "@point_of_sale/../tests/unit/data/pos_payment_method.data";

const P2P_REQUEST_ID = "250102070607078E010040377";
const TRANSACTION_ID = "250102070624795E020088174";

const TERMINAL_RESPONSE = {
    authCode: "D12345",
    cardLastFourDigit: "1234",
    txnId: TRANSACTION_ID,
    paymentMode: "CARD",
    paymentCardBrand: "VISA",
    paymentCardType: "DEBIT",
    nameOnCard: "John Doe",
    acquirerCode: "HDFC",
};

const IST_OFFSET = 19800000;

patch(PosPaymentMethod.prototype, {
    get razorpayState() {
        if (!this._razorpayState) {
            this._razorpayState = { externalRefNumber: null };
        }
        return this._razorpayState;
    },

    razorpay_make_payment_request(ids, data) {
        if (!data.referenceId) {
            return { error: "`externalRefNumber` field is empty." };
        }
        this.razorpayState.externalRefNumber = data.referenceId;
        return { success: true, p2pRequestId: P2P_REQUEST_ID };
    },

    razorpay_fetch_payment_status(ids, data) {
        if (!data.p2pRequestId) {
            return { error: "The 'origP2pRequestId' field is required in the JSON payload." };
        }
        return {
            ...TERMINAL_RESPONSE,
            status: "AUTHORIZED",
            externalRefNumber: this.razorpayState.externalRefNumber,
            reverseReferenceNumber: "RR6A55BBEA34E2",
            createdTime: Date.now() + IST_OFFSET,
            p2pRequestId: data.p2pRequestId,
            settlementStatus: "PENDING",
        };
    },

    razorpay_cancel_payment_request(ids, data) {
        return { error: "Razorpay POS transaction canceled successfully" };
    },

    razorpay_make_refund_request(ids, data) {
        return {
            ...TERMINAL_RESPONSE,
            status: data.refund_type === "refund" ? "REFUNDED" : "VOIDED",
            externalRefNumber: data.externalRefNumber,
            reverseReferenceNumber: "RR6A55BBEA34E2",
            postingDate: Date.now() + IST_OFFSET,
        };
    },
});

PosPaymentMethod._records.push({
    id: 7,
    name: "Razorpay",
    payment_provider: "razorpay",
    payment_method_type: "terminal",
    type: "bank",
    image: false,
    sequence: 6,
    default_qr: false,
    config_ids: [1],
});
