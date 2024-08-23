/** @odoo-module **/

import { useAskRecurrenceUpdatePolicy } from "../ask_recurrence_update_policy_hook";
import { CalendarModel } from "@web/views/calendar/calendar_model";

export class CalendarBisModel extends CalendarModel {
    setup() {
        super.setup(...arguments);
        this.askRecurrenceUpdatePolicy = useAskRecurrenceUpdatePolicy();
    }

    /**
     * @override
     */
    buildRawRecord(partialRecord, options = {}) {
        const result = super.buildRawRecord(partialRecord);
        if (partialRecord.recurrenceUpdate) {
            result.edit = partialRecord.recurrenceUpdate;
        }
        return result;
    }

    /**
     * @override
     *
     * Upon updating a record with recurrence, we need to ask how it will affect recurrent events.
     */
    async updateRecord(record) {
        const rec = this.records[record.id];
        if (rec.rawRecord.is_recurring) {
            const recurrenceUpdate = await this.askRecurrenceUpdatePolicy(this.dialog);
            record.recurrenceUpdate = recurrenceUpdate;
        }
        return await super.updateRecord(...arguments);
    }
}
