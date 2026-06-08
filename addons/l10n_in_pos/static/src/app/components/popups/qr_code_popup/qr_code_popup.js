import { props, types } from "@odoo/owl";
import { QRPopup } from "@point_of_sale/app/components/popups/qr_code_popup/qr_code_popup";
import { patch } from "@web/core/utils/patch";

patch(QRPopup.prototype, {
    setup() {
        super.setup();
        this.l10nInPosProps = props({
            "paymentMethod?": types.object(),
        });
    },
});
