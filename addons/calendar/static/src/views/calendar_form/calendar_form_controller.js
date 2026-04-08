import { FormController } from "@web/views/form/form_controller";
import { useDeleteCalendarEvent } from "@calendar/views/hooks";
import { useService } from "@web/core/utils/hooks";

export class CalendarFormController extends FormController {
    setup() {
        super.setup();
        this.actionService = useService("action");
        this.deleteCalendarEvent = useDeleteCalendarEvent({ model: this.model });
    }

    /**
     * @override
     */
    async beforeExecuteActionButton(clickParams) {
        const action = clickParams.name;
        if (action === "clear_videocall_location") {
            this.model.root.clearLocation();
            return false;
        } else if (action === "set_discuss_videocall_location") {
            this.model.root.setLocation();
            return false;
        }
        return super.beforeExecuteActionButton(...arguments);
    }

    /**
     * @override
     */
    async deleteRecord() {
        const record = this.model.root;
        await this.deleteCalendarEvent({
            resId: record.resId,
            currentAttendeeId: record.data.current_attendee.id,
            currentStatus: record.data.current_status,
            organizerId: record.data.user_id.id,
            partnerIds: record.data.partner_ids.resIds,
            recurrency: record.data.recurrency,
            start: record.data.start,
            deleteConfirmationDialogProps: this.deleteConfirmationDialogProps,
            nextAction: { type: "ir.actions.act_url", target: "self", url: "/odoo/calendar" },
        });
    }
}
