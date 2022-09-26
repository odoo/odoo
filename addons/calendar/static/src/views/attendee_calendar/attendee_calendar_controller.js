/** @odoo-module **/

import { CalendarController } from "@web/views/calendar/calendar_controller";
import { useService } from "@web/core/utils/hooks";

export class AttendeeCalendarController extends CalendarController {
    setup() {
        super.setup();
        this.actionService = useService("action");
        this.user = useService("user");
        this.orm = useService("orm");
    }

    onClickAddButton() {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'calendar.event',
            views: [[false, 'form']],
        }, {
            additionalContext: this.props.context,
        });
    }

    /**
     * @override
     *
     * If the event is deleted by the organizer, the event is deleted, otherwise it is declined.
     */
    deleteRecord(record) {
        if (this.user.partnerId === record.attendeeId && this.user.partnerId === record.rawRecord.partner_id[0]) {
            super.deleteRecord(...arguments);
        } else {
            // Decline event
            this.orm.call(
                "calendar.attendee",
                "do_decline",
                [record.attendeeId],
            ).then(this.model.load.bind(this.model));
        }
    }

    configureCalendarProviderSync(providerName) {
        this.actionService.doAction({
            name: this.env._t('Connect your Calendar'),
            type: 'ir.actions.act_window',
            res_model: 'calendar.provider.config',
            views: [[false, "form"]],
            view_mode: "form",
            target: 'new',
            context: {
                'default_external_calendar_provider': providerName,
                'dialog_size': 'medium',
            }
        });
    }
}
AttendeeCalendarController.template = "calendar.AttendeeCalendarController";
