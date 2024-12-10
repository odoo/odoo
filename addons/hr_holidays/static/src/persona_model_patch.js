/** @odoo-module */

import { Persona } from "@mail/core/common/persona_model";
import { patch } from "@web/core/utils/patch";
import { debounce } from "@web/core/utils/timing";

patch(Persona.prototype, {
    /**
     * @overwrite
     */
    _handleImStatusUpdate() {
        this.debouncedSetImStatus = debounce((newStatus) => {
            if (newStatus == "online" && this.out_of_office_date_end) {
                this.im_status = "leave_online";
            } else if (newStatus == "offline" && this.out_of_office_date_end) {
                this.im_status = "leave_offline";
            } else if (newStatus == "away" && this.out_of_office_date_end) {
                this.im_status = "leave_away";
            } else {
                this.im_status = newStatus;
            }
        }, this.IM_STATUS_DEBOUNCE_DELAY);
    },
});
