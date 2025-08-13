import { AttendeeCalendarController } from "@calendar/views/attendee_calendar/attendee_calendar_controller";
import { GoogleCalendarComponent } from "@google_calendar/views/google_calendar/google_calendar_component";

import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog, AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(AttendeeCalendarController, {
    components: { ...AttendeeCalendarController.components, GoogleCalendarComponent },
});