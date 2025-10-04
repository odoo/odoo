import { registry } from "@web/core/registry";
import { Base } from "@point_of_sale/app/models/related_models";

export class PosPaymentMethod extends Base {
    static pythonModel = "pos.payment.method";

    get isExternalQR() {
        return this.payment_method_type === "external_qr";
    }

    get isExternalStickerQR() {
        return this.payment_method_type === "external_qr" && this.external_qr_usage === "sticker";
    }

    get isExternalDisplayQR() {
        return this.payment_method_type === "external_qr" && this.external_qr_usage === "display";
    }
}

registry.category("pos_available_models").add(PosPaymentMethod.pythonModel, PosPaymentMethod);
