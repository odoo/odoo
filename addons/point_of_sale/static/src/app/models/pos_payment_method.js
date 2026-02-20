import { registry } from "@web/core/registry";
import { Base } from "./related_models";

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
}

registry.category("pos_available_models").add(PosPaymentMethod.pythonModel, PosPaymentMethod);
