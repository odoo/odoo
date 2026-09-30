import { _t } from "@web/core/l10n/translation";
import { CalendarController } from "@web/views/calendar/calendar_controller";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { onWillStart } from "@odoo/owl";
import { CalendarQuickCreate } from "@calendar/views/calendar_form/calendar_quick_create";
export class AttendeeCalendarController extends CalendarController {
    static template = "calendar.AttendeeCalendarController";
    static components = {
        ...AttendeeCalendarController.components,
        QuickCreateFormView: CalendarQuickCreate,
    };

    setup() {
        super.setup();
        this.actionService = useService("action");
        this.orm = useService("orm");
        onWillStart(async () => {
            this.isSystemUser = await user.hasGroup("base.group_system");
        });
    }

    onClickAddButton() {
        this.actionService.doAction(
            {
                type: "ir.actions.act_window",
                res_model: "calendar.event",
                views: [[false, "form"]],
            },
            {
                additionalContext: this.props.context,
            }
        );
    }

    goToFullEvent(resId, additionalContext) {
        this.actionService.doAction(
            {
                type: "ir.actions.act_window",
                res_model: "calendar.event",
                views: [[false, "form"]],
                res_id: resId || false,
            },
            {
                additionalContext: {
                    ...this.props.context,
                    ...additionalContext,
                },
            }
        );
    }

    getQuickCreateFormViewProps(record) {
        const props = super.getQuickCreateFormViewProps(record);
        const onDialogClosed = () => {
            this.model.load();
        };
        return {
            ...props,
            size: "md",
            context: { ...props.context, ...this.props.context },
            onRecordSaved: () => onDialogClosed(),
        };
    }

    async editRecord(record, context = {}) {
        if (record.id) {
            return this.goToFullEvent(record.id, context);
        }
    }

    /**
     * @override
     *
     * If the event is deleted by the organizer, the event is deleted, otherwise it is declined.
     */
    deleteRecord(record) {
        if (
            user.partnerId === record.attendeeId &&
            user.partnerId === record.rawRecord.partner_id[0]
        ) {
            if (record.rawRecord.recurrency) {
                this.openRecurringDeletionWizard(record);
            } else if (user.partnerId === record.attendeeId &&
                record.rawRecord.attendees_count == 1) {
                super.deleteRecord(...arguments);
            } else {
                this.orm.call("calendar.event", "action_unlink_event", [
                    record.id,
                    record.attendeeId,
                ])
                .then((action) => {
                    if (action && action.context) {
                        this.actionService.doAction(action);
                    } else {
                        location.reload();
                    }
                });
            }
        } else {
            // Decline event
            this.orm
                .call("calendar.attendee", "do_decline", [record.calendarAttendeeId])
                .then(this.model.load.bind(this.model));
        }
    }

    openRecurringDeletionWizard(record) {
        this.actionService.doAction(
            {
                type: "ir.actions.act_window",
                res_model: "calendar.popover.delete.wizard",
                views: [[false, "form"]],
                view_mode: "form",
                name: "Delete Recurring Event",
                context: {
                    default_calendar_event_id: record.id,
                    default_attendee_id: record.attendeeId,
                    form_view_ref: 'calendar.calendar_popover_delete_view',
                },
                target: "new",
            },
            {
                onClose: () => {
                    this.model.load();
                },
            }
        );
    }

    configureCalendarProviderSync(providerName) {
        this.actionService.doAction({
            name: _t("Connect your Calendar"),
            type: "ir.actions.act_window",
            res_model: "calendar.provider.config",
            views: [[false, "form"]],
            view_mode: "form",
            target: "new",
            context: {
                default_external_calendar_provider: providerName,
                dialog_size: "medium",
            },
        });
    }
}
