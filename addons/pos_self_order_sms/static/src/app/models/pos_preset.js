import { PosPreset } from "@point_of_sale/app/models/pos_preset";
import { patch } from "@web/core/utils/patch";

patch(PosPreset.prototype, {
    get needsPhone() {
        return (
            super.needsPhone ||
            (this.identification !== "none" && Boolean(this.sms_receipt_template_id))
        );
    },
});
