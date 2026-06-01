/* @odoo-module */

import { personaService, PersonaService } from "@mail/core/common/persona_service";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

const { DateTime } = luxon;

patch(personaService, {
    dependencies: [...new Set([...personaService.dependencies, "user"])],
});

patch(PersonaService.prototype, {
    setup(env, services) {
        super.setup(env, services);
        this.userService = services.user;
    },

    outOfOfficeText(persona) {
        if (!persona.out_of_office_date_end) {
            return "";
        }
        const date = deserializeDateTime(persona.out_of_office_date_end);
        const options = { ...DateTime.DATE_MED, timeZone:"UTC" };
        const fdate = date.toLocaleString(options);
        return _t("Out of office until %s", fdate);
    },
});
