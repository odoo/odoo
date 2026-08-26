import { _t } from "@web/core/l10n/translation";
import { CustomerFacingQR } from "@point_of_sale/customer_display/customer_facing_qr";

export class PaywayCustomerFacingQR extends CustomerFacingQR {
    static template = "aba_payway_qr_payment_pos_odoo.PaywayCustomerFacingQR";
    setup() {
        super.setup();
    }
}
