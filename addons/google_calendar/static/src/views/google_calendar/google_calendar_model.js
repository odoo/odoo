import { AttendeeCalendarModel } from "@calendar/views/attendee_calendar/attendee_calendar_model";
import { patch } from "@web/core/utils/patch";

patch(AttendeeCalendarModel.prototype, {
    setup(params) {
        super.setup(...arguments);
        this.isAlive = params.isAlive;
        this.googlePendingSync = false;
    },

    /**
     * @override
     */
    async updateData() {
        if (this.googlePendingSync) {
            return super.updateData(...arguments);
        }

        try {
            console.log("before race");
            await Promise.race([
                new Promise(resolve => setTimeout(resolve, 1000)),
                this.syncGoogleCalendar(),
            ]);
            console.log("after race");
        } catch (error) {
            if (error.event) {
                error.event.preventDefault();
            }
            console.error("Could not synchronize Google events now.", error);
            this.googlePendingSync = false;
        }

        if (this.isAlive()) {
            return super.updateData(...arguments);
        }
        return new Promise(() => {});
    },

    async syncGoogleCalendar() {
        this.googlePendingSync = true;
        console.log("before await trigger");
        this.env.bus.trigger("sync_google_calendar");
        console.log("after await trigger");
        this.googlePendingSync = false;
    }
});
