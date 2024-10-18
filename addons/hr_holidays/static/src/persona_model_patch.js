import { Persona } from "@mail/core/common/persona_model";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
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
        const currentDate = new Date();
        const date = deserializeDateTime(this.out_of_office_date_end);
        // const options = { day: "numeric", month: "short" };
        if (currentDate.getFullYear() !== date.year) {
            // options.year = "numeric";
        }
        let localeCode = user.lang.replace(/_/g, "-");
        if (localeCode === "sr@latin") {
            localeCode = "sr-Latn-RS";
        }
        // const fdate = date.toLocaleString(DateTime.TIME_SHORT);
        const fdate = date.toLocaleString(DateTime.DATE_MED);
        // const formattedDate = date.toLocaleDateString(localeCode, options);
        return _t("Out of office until %s", fdate);
    },
});
