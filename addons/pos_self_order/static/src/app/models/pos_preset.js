import { PosPreset } from "@point_of_sale/app/models/pos_preset";
import { patch } from "@web/core/utils/patch";

patch(PosPreset.prototype, {
    get needsEmail() {
        return Boolean(this.mail_template_id);
    },
});
