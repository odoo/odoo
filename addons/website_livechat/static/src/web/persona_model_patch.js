import { Persona } from "@mail/core/common/persona_model";

import { patch } from "@web/core/utils/patch";
import { deserializeDateTime } from "@web/core/l10n/dates";

const { DateTime } = luxon;

patch(Persona.prototype, {
    get historyLocalized() {
        const history = [];
        for (const h of this.history_data ?? []) {
            const [label, date] = h;
            const time = deserializeDateTime(date).toLocaleString(DateTime.TIME_24_SIMPLE);
            history.push(`${label} (${time})`);
        }
        return history.join(" → ");
    },
});
