import { registry } from "@web/core/registry";
import { Base } from "./related_models";
import { formatCurrency } from "@point_of_sale/app/models/utils/currency";
const { DateTime } = luxon;

export class PosPayment extends Base {
    static pythonModel = "pos.payment";

    setup(vals) {
        super.setup(...arguments);
        if (!this.payment_date) {
            this.payment_date = DateTime.now();
        }
        this.amount = vals.amount || 0;
        this.ticket = vals.ticket || "";
    }

    initState() {
        super.initState();
        this.uiState = { initStateDate: DateTime.now() };
    }

    get config() {
        return this.models["pos.config"].get(odoo.pos_config_id);
    }

    get currency() {
        return this.foreign_currency_id || this.pos_order_id.currency;
    }

    get isDifferentCurrency() {
        return (
            this.foreign_currency_id &&
            this.foreign_currency_id.id !== this.pos_order_id.currency.id
        );
    }

    getQrPopupProps() {
        return {
            qrCode: this.qr_code,
            amount: formatCurrency(this.amount_currency || this.getAmount(), this.currency),
            provider: this.payment_provider,
        };
    }

    /**
     * Kept in snake_case for consistency with existing model fields.
     */
    get payment_interface() {
        return this.payment_method_id.payment_interface;
    }

    /**
     * Kept in snake_case for consistency with existing model fields.
     */
    get payment_provider() {
        return this.payment_method_id.payment_provider;
    }

    get useProvider() {
        return this.payment_method_id.useProvider;
    }

    get useBankTransfer() {
        return this.payment_method_id.useBankTransfer;
    }

    get usePaymentInterface() {
        return this.payment_method_id.usePaymentInterface;
    }

    get displayName() {
        return this.payment_method_id.name;
    }

    isSelected() {
        return this.pos_order_id?.uiState?.selected_paymentline_uuid === this.uuid;
    }

    setAmount(value, currency = this.pos_order_id.currency) {
        this.pos_order_id.assertEditable();

        if (currency != this.pos_order_id.currency) {
            this.amount_currency = parseFloat(value) || 0;
            this.amount = this.pos_order_id.currency.round(
                this.currency.convertToDefaultCurrency(this.amount_currency)
            );
        } else {
            this.amount = this.pos_order_id.currency.round(parseFloat(value) || 0);
            this.amount_currency = this.currency.convert(this.amount);
        }
    }

    getAmount() {
        return this.amount || 0;
    }

    get isSettled() {
        return !this.usePaymentInterface || this.payment_status === "done";
    }

    get isProcessing() {
        return [
            "waiting",
            "waiting_cancel",
            "waiting_card",
            "waiting_scan",
            "waiting_capture",
            "force_done",
        ].includes(this.payment_status);
    }

    get isAmountEditable() {
        return !this.usePaymentInterface || ["pending", "retry"].includes(this.payment_status);
    }

    get isRefund() {
        return this.amount < 0;
    }

    // ----- Payment Flows, run by the payment interface -----
    async pay() {
        return this.payment_interface.pay(this);
    }

    async cancelPayment() {
        return this.payment_interface.cancelPayment(this);
    }

    forceDone() {
        return this.payment_interface.forceDone(this);
    }

    forceCancel() {
        return this.payment_interface.forceCancel(this);
    }

    /**
     * @param {object} - refundedPaymentLine
     * Override in dependent modules to update the refund payment line with the refunded payment line
     */
    updateRefundPaymentLine(refundedPaymentLine) {}

    canBeAdjusted() {
        if (this.payment_interface) {
            return this.payment_interface.isLineAdjustable(this);
        }
        return this.payment_method_id.type !== "cash";
    }

    /**
     * @returns {Promise<boolean>} true when the amount was adjusted. Without
     * a payment interface, nothing to adjust: the amount stays as it is.
     */
    async adjustAmount(amount) {
        if (!this.payment_interface) {
            return true;
        }
        return this.payment_interface.adjustAmount(this, amount);
    }
}

registry.category("pos_available_models").add(PosPayment.pythonModel, PosPayment);
