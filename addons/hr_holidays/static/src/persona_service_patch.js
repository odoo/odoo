import { PersonaService } from "@mail/core/common/persona_service";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { patch } from "@web/core/utils/patch";

const { DateTime } = luxon;

patch(PersonaService.prototype, {
    outOfOfficeText(persona) {
        if (!persona.out_of_office_date_end) {
            return "";
        }
        const currentDate = new Date();
        const date = deserializeDateTime(persona.out_of_office_date_end);
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
