import { Persona } from "@mail/core/common/persona_model";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

const { DateTime } = luxon;

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

    get outOfOfficeText() {
        if (!this.out_of_office_date_end) {
            return "";
        }
        const date = deserializeDateTime(this.out_of_office_date_end);
        const fdate = date.toLocaleString(DateTime.DATE_MED);
        return _t("Back on %s", fdate);
    },
});
