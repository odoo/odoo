import { qrPopupProps } from "@point_of_sale/app/components/popups/qr_code_popup/qr_code_popup";
import { t } from "@odoo/owl";

Object.assign(qrPopupProps, {
    paymentMethod: t.object().optional(),
});
