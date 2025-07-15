import { patch } from "@web/core/utils/patch";
import { Persona } from "@mail/core/common/persona_model";
import { deserializeDateTime } from "@web/core/l10n/dates";

const { DateTime } = luxon;

patch(Persona.prototype, {
    get historyString() {
        if (!this.history_data || !Array.isArray(this.history_data)) {
            return "";
        }
        const history = [];
        for (const h of this.history_data) {
            if (!Array.isArray(h) || h.length !== 2) {
                return "";
            }
            const time = deserializeDateTime(h[1]).toLocaleString(DateTime.TIME_24_SIMPLE);
            history.push(`${h[0]} (${time})`);
        }
        return history.join(" → ");
    },
});
