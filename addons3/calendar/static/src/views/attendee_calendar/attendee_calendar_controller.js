/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { CalendarController } from "@web/views/calendar/calendar_controller";
import { useService } from "@web/core/utils/hooks";
import { onWillStart } from "@odoo/owl";
import { CalendarQuickCreate } from "@calendar/views/calendar_form/calendar_quick_create";
export class AttendeeCalendarController extends CalendarController {
    setup() {
        super.setup();
        this.actionService = useService("action");
        this.user = useService("user");
        this.orm = useService("orm");
        onWillStart(async () => {
            this.isSystemUser = await this.user.hasGroup('base.group_system');
        });
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

    goToFullEvent (resId, additionalContext) {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'calendar.event',
            views: [[false, 'form']],
            res_id: resId || false,
        }, {
            additionalContext
        });
    }

    getQuickCreateFormViewProps(record) {
        const props = super.getQuickCreateFormViewProps(record);
        const onDialogClosed = () => {
            this.model.load();
        };
        return {
            ...props,
            size: "md",
            goToFullEvent: (contextData) => {
                const fullContext = {
                    ...props.context,
                    ...contextData
                };
                this.goToFullEvent(false, fullContext)
            },
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
        if (this.user.partnerId === record.attendeeId && this.user.partnerId === record.rawRecord.partner_id[0]) {
            if (record.rawRecord.recurrency) {
                this.openRecurringDeletionWizard(record);
            } else {
                super.deleteRecord(...arguments);
            }
        } else {
            // Decline event
            this.orm.call(
                "calendar.attendee",
                "do_decline",
                [record.calendarAttendeeId],
            ).then(this.model.load.bind(this.model));
        }
    }

    openRecurringDeletionWizard(record) {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'calendar.popover.delete.wizard',
            views: [[false, 'form']],
            view_mode: "form",
            name: 'Delete Recurring Event',
            context: {'default_record': record.id},
            target: 'new'
        }, {
            onClose: () => {
                location.reload();
            },
        });
    }

    configureCalendarProviderSync(providerName) {
        this.actionService.doAction({
            name: _t('Connect your Calendar'),
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
AttendeeCalendarController.components = {
    ...AttendeeCalendarController.components,
    QuickCreateFormView: CalendarQuickCreate,
}
