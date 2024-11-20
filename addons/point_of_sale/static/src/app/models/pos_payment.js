import { registry } from "@web/core/registry";
import { Base } from "./related_models";
import { serializeDateTime } from "@web/core/l10n/dates";
import { roundDecimals } from "@web/core/utils/numbers";
import { uuidv4 } from "@point_of_sale/utils";

const { DateTime } = luxon;

export class PosPayment extends Base {
    static pythonModel = "pos.payment";

    setup(vals) {
        super.setup(...arguments);
        this.payment_date = serializeDateTime(DateTime.now());
        this.uuid = vals.uuid ? vals.uuid : uuidv4();
        this.amount = vals.amount || 0;
        this.ticket = vals.ticket || "";
    }

    isSelected() {
        return this.pos_order_id?.uiState?.selected_paymentline_uuid === this.uuid;
    }

    setAmount(value) {
        this.pos_order_id.assetEditable();
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

    exportForPrinting() {
        return {
            amount: this.getAmount(),
            name: this.payment_method_id.name,
            ticket: this.ticket,
        };
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
}

registry.category("pos_available_models").add(PosPayment.pythonModel, PosPayment);
