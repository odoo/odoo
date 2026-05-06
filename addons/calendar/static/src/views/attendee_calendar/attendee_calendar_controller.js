import { _t } from "@web/core/l10n/translation";
import { AttendeeCalendarSidePanel } from "@calendar/views/attendee_calendar/side_panel/attendee_calendar_side_panel";
import { CalendarController } from "@web/views/calendar/calendar_controller";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useCancelCalendarEvent } from "@calendar/views/hooks";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { onWillStart } from "@odoo/owl";
import { CalendarQuickCreate } from "@calendar/views/calendar_form/calendar_quick_create";
export class AttendeeCalendarController extends CalendarController {
    static template = "calendar.AttendeeCalendarController";
    static components = {
        ...AttendeeCalendarController.components,
        CalendarSidePanel: AttendeeCalendarSidePanel,
        QuickCreateFormView: CalendarQuickCreate,
    };

    setup() {
        super.setup();
        this.actionService = useService("action");
        this.cancelCalendarEvent = useCancelCalendarEvent();
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
        return {
            ...props,
            size: "md",
            context: { ...props.context, ...this.props.context },
            onRecordSave: async (record) => {
                // first ask fields for their changes, in case user was still typing
                await record.getChanges();
                const updates = {
                    ...(!record.data.name && { name: _t("(No Title)") }),
                    ...(record.data.allday && { show_as: "free" }),
                };
                if (Object.keys(updates).length) {
                    await record.update(updates);
                }
                const saved = await record.save({ reload: false });
                if (saved) {
                    this.model.load();
                }
                return saved;
            },
        };
    }

    async editRecord(record, context = {}) {
        if (record.id) {
            return this.goToFullEvent(record.id, context);
        }
    }

    /**
     * @override
     */
    async deleteRecord(record) {
        await this.cancelCalendarEvent({
            requestedAction: "delete",
            resId: record.id,
            currentAttendeeId: record.calendarAttendeeId,
            currentStatus: record.attendeeStatus,
            organizerId: record.rawRecord.user_id[0],
            partnerIds: record.rawRecord.partner_ids,
            recurrency: record.rawRecord.recurrency,
            start: record.start,
            fallback: () => this.displayDialog(ConfirmationDialog, this.deleteConfirmationDialogProps(record)),
        });
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
