import { CalendarModel } from "@web/views/calendar/calendar_model";
import { deserializeDate } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";

import { onWillStart } from "@odoo/owl";


export class SlotCalendarModel extends CalendarModel {
    static services = [...CalendarModel.services, "orm"];

    setup() {
        super.setup(...arguments);
        this.data.slots = {};
        this.timeFormat = localization.timeFormat.replace(":ss", "");

        onWillStart(async () => {
            const slots = await this.orm.call("event.event", "generate_slots", [this.env.searchModel.context.event_id]);
            if (slots.length) {
                this.createSlots(slots);
                // Set the calendar initial date to be the earliest slot date
                this.meta.date = slots.map(slot => deserializeDate(slot.start)).reduce((earliestDate, currentDate) => {
                    return currentDate < earliestDate ? currentDate : earliestDate;
                });
            }
        });
    }

    createSlots(slots_list) {
        slots_list.forEach((slot, index) => {
            const start = luxon.DateTime.fromISO(slot["start"].replace(' ', 'T'));
            const end = luxon.DateTime.fromISO(slot["end"].replace(' ', 'T'));
            this.data.slots[index] = {
                id: index,
                title: `${start.toFormat(this.timeFormat)} - ${end.toFormat(this.timeFormat)}`,
                start: start,
                end: end,
            };
        });
    }
}
