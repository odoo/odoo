import { GanttController } from "@web_gantt/gantt_controller";

const { DateTime } = luxon;

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
     * The stop datetime is set by default to start + 1 hour to override the calendar.event's default_stop, which is currently setting the stop based on now instead of start.
     * The stop datetime will be updated in the default_get method on python side to match the appointment type duration.
    */
    onAddClicked() {
        const focusDate = this.getCurrentFocusDate();
        const now = DateTime.now();
        const start =
            now.minute > 30
                ? focusDate.set({ hour: now.hour + 1, minute: 0, second: 0 })
                : focusDate.set({ hour: now.hour, minute: 30, second: 0 });
        const stop = start.plus({ hour: 1 });
        const context = this.model.getDialogContext({ start, stop, withDefault: true });
        this.create(context);
    }
}
