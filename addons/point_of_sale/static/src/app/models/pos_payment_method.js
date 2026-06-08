import { registry } from "@web/core/registry";
import { Base } from "./related_models";
import { _t } from "@web/core/l10n/translation";

export class PosPaymentMethod extends Base {
    static pythonModel = "pos.payment.method";

    get useTerminal() {
        return this.payment_method_type === "terminal";
    }

    get useQr() {
        return this.payment_method_type === "external_qr";
    }

    get useBankQrCode() {
        return this.payment_method_type === "bank_qr_code";
    }

    /**
     * Check orders to know if the payment terminal is available for the current order.
     * This is useful for payment methods that require specific conditions to be met,
     * such as Bancontact which requires a single payment in progress per sticker.
     * The method is called with the current payment method and line.
     */
    _checkOrder({ order, paymentline }) {
        const hasProcessingPayment = order.payment_ids.some(
            (pl) =>
                this.payment_method_type === pl.payment_method_id.payment_method_type &&
                pl.uuid !== paymentline?.uuid &&
                pl.isProcessing()
        );
        if (hasProcessingPayment) {
            return {
                status: false,
                message: _t("There is already an electronic payment in progress."),
            };
        }
        return { status: true, message: "" };
    }

    /**
     * Called to check if a payment request can be sent for a given payment method and line.
     */
    getPaymentInterfaceStates({ paymentline } = {}) {
        const openOrder = this.models["pos.order"].filter((o) => !o.finalized);
        for (const order of openOrder) {
            const result = this._checkOrder({ order, paymentline });
            if (!result.status) {
                return result;
            }
        }

        return { status: true, message: "" };
    }
}

registry.category("pos_available_models").add(PosPaymentMethod.pythonModel, PosPaymentMethod);
