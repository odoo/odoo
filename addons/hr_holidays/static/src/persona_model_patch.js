import { Persona } from "@mail/core/common/persona_model";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

const { DateTime } = luxon;

export function getOutOfOfficeDateEndText(datetime) {
    const foptions = { ...DateTime.DATE_MED };
    const dt = deserializeDateTime(datetime);
    if (dt.year === DateTime.now().year) {
        foptions.year = undefined;
    }
    const fdate = dt.toLocaleString(foptions);
    return _t("Back on %(date)s", { date: fdate });
}

patch(Persona.prototype, {
    get outOfOfficeDateEndText() {
        if (!this.leave_date_to) {
            return "";
        }
        return getOutOfOfficeDateEndText(this.leave_date_to);
    },
});
