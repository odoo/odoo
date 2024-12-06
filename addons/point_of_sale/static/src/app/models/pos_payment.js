import { registry } from "@web/core/registry";
import { Base } from "./related_models";
import { roundDecimals } from "@web/core/utils/numbers";
import { uuidv4 } from "@point_of_sale/utils";

const { DateTime } = luxon;

export class PosPayment extends Base {
    static pythonModel = "pos.payment";

    setup(vals) {
        super.setup(...arguments);
        this.payment_date = DateTime.now();
        this.uuid = vals.uuid ? vals.uuid : uuidv4();
        this.amount = vals.amount || 0;
        this.ticket = vals.ticket || "";
    }

    isSelected() {
        return this.pos_order_id?.uiState?.selected_paymentline_uuid === this.uuid;
    }

    setAmount(value) {
        this.pos_order_id.assertEditable();
        this.amount = roundDecimals(
            parseFloat(value) || 0,
            this.pos_order_id.currency.decimal_places
        );
    }

    getAmount() {
        return this.amount || 0;
    }

    getPaymentStatus() {
        return this.payment_status;
    }

    setPaymentStatus(value) {
        this.payment_status = value;
    }

    isDone() {
        return this.getPaymentStatus()
            ? this.getPaymentStatus() === "done" || this.getPaymentStatus() === "reversed"
            : true;
    }

    setCashierReceipt(value) {
        this.cashier_receipt = value;
    }

    setReceiptInfo(value) {
        this.ticket += value;
    }

    isElectronic() {
        return Boolean(this.getPaymentStatus());
    }

    async pay() {
        this.setPaymentStatus("waiting");

        return this.handlePaymentResponse(
            await this.payment_method_id.payment_terminal.sendPaymentRequest(this.uuid)
        );
    }

    handlePaymentResponse(isPaymentSuccessful) {
        if (isPaymentSuccessful) {
            this.setPaymentStatus("done");
            if (this.payment_method_id.payment_method_type !== "qr_code") {
                this.can_be_reversed = this.payment_method_id.payment_terminal.supports_reversals;
            }
        } else {
            this.setPaymentStatus("retry");
        }
        return isPaymentSuccessful;
    }

    updateRefundPaymentLine(refundedPaymentLine) {
        this.transaction_id = refundedPaymentLine.transaction_id;
    }
}

registry.category("pos_available_models").add(PosPayment.pythonModel, PosPayment);
