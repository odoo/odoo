import { PosPreset } from "@point_of_sale/app/models/pos_preset";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

const { DateTime } = luxon;

patch(PosPreset.prototype, {
    get needsEmail() {
        return Boolean(this.mail_template_id);
    },

    slotPrefix(dateObj) {
        const today = DateTime.now();
        const slotDate = dateObj.toFormat("D");
        if (today.toFormat("D") === slotDate) {
            return _t("Today");
        } else if (today.plus({ days: 1 }).toFormat("D") === slotDate) {
            return _t("Tommorrow");
        }
        return "";
    },

    formatDate(dateObj) {
        const formattedDate = dateObj.toFormat("MMM d");
        const prefix = this.slotPrefix(dateObj);
        if (prefix) {
            return `${prefix} (${formattedDate})`;
        }
        return formattedDate;
    },
});
