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

    set_amount(value) {
        this.pos_order_id.assert_editable();
        this.update({
            amount: roundDecimals(
                parseFloat(value) || 0,
                this.pos_order_id.currency.decimal_places
            ),
        });
    }

    get_amount() {
        return this.amount || 0;
    }

    get_payment_status() {
        return this.payment_status;
    }

    set_payment_status(value) {
        this.update({ payment_status: value });
    }

    is_done() {
        return this.get_payment_status()
            ? this.get_payment_status() === "done" || this.get_payment_status() === "reversed"
            : true;
    }

    set_cashier_receipt(value) {
        this.cashier_receipt = value;
    }

    set_receipt_info(value) {
        this.ticket += value;
    }

    export_for_printing() {
        return {
            amount: this.get_amount(),
            name: this.payment_method_id.name,
            ticket: this.ticket,
        };
    }

    is_electronic() {
        return Boolean(this.get_payment_status());
    }

    async pay() {
        this.set_payment_status("waiting");

        return this.handle_payment_response(
            await this.payment_method_id.payment_terminal.send_payment_request(this.uuid)
        );
    }

    handle_payment_response(isPaymentSuccessful) {
        if (isPaymentSuccessful) {
            this.set_payment_status("done");
            if (this.payment_method_id.payment_method_type !== "qr_code") {
                this.can_be_reversed = this.payment_method_id.payment_terminal.supports_reversals;
            }
        } else {
            this.set_payment_status("retry");
        }
        return isPaymentSuccessful;
    }
}

registry.category("pos_available_models").add(PosPayment.pythonModel, PosPayment);
