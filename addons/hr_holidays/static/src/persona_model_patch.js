import { Persona } from "@mail/core/common/persona_model";
import { patch } from "@web/core/utils/patch";

patch(Persona.prototype, {
    updateImStatus(newStatus) {
        if (newStatus == "online" && this.out_of_office_date_end) {
            this.im_status = "leave_online";
        } else if (newStatus == "offline" && this.out_of_office_date_end) {
            this.im_status = "leave_offline";
        } else if (newStatus == "away" && this.out_of_office_date_end) {
            this.im_status = "leave_away";
        } else {
            return super.updateImStatus(...arguments);
        }
    },
});
