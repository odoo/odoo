/* @odoo-module */

import { GanttController } from "@web_gantt/gantt_controller";

export class AppointmentBookingGanttController extends GanttController {

    /**
     * @override
     */
    create(context) {
        super.create({...context, 'booking_gantt_create_record': true})
    }

    /**
     * @override
    */
    get showNoContentHelp() {
        // show if no named row, as it implies both no record and no forced group from resources
        return !this.model.data.rows || (this.model.data.rows.length == 1 && !this.model.data.rows[0].name)
    }

    /**
     * @override
     * When creating a new booking using the "New" button, round the start datetime to the next
     * half-hour (e.g. 10:12 => 10:30, 11:34 => 12:00).
     * The stop datetime is handle by the default_get method on python side which add the appointment type duration.
    */
    onAddClicked() {
        const { focusDate } = this.model.metaData;
        const start = focusDate.minute > 30 ? focusDate.plus({ hour: 1 }).set({ minute: 0, second: 0 }) : focusDate.set({ minute: 30, second: 0 });
        const context = this.model.getDialogContext({ start, withDefault: true });
        this.create(context);
    }
}
