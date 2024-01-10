/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { CalendarController } from "@web/views/calendar/calendar_controller";
import { CalendarQuickCreate } from "@calendar_bis/views/form/calendar_quick_create";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { onWillStart } from "@odoo/owl";
import { useAskRecurrenceUpdatePolicy } from "../ask_recurrence_update_policy_hook";

export class CalendarBisController extends CalendarController {
    static template = "calendar_bis.CalendarBisController";
    static components = {
        ...CalendarController.components,
        QuickCreateFormView: CalendarQuickCreate,
    }

    setup() {
        super.setup();
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.askRecurrenceUpdatePolicy = useAskRecurrenceUpdatePolicy()
        onWillStart(async () => {
            this.isSystemUser = await user.hasGroup("base.group_system");
        });
    }

    onClickAddButton() {
        this.actionService.doAction(
            {
                type: "ir.actions.act_window",
                res_model: "calendar.timeslot",
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
                res_model: "calendar.timeslot",
                views: [[false, "form"]],
                res_id: resId || false,
            },
            {
                additionalContext,
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
            goToFullEvent: (contextData) => {
                const fullContext = {
                    ...props.context,
                    ...contextData,
                };
                this.goToFullEvent(false, fullContext);
            },
            onRecordSaved: () => onDialogClosed(),
        };
    }

    async editRecord(record, context = {}) {
        if (record.id) {
            return this.goToFullEvent(record.id, context);
        }
        return super.editRecord(record, context);
    }

    /**
     * @override
     *
     * If the event is deleted by the organizer, the event is deleted, otherwise it is declined.
     */
    async deleteRecord(record) {
        if (
            user.partnerId === record.rawRecord.partner_id[0]
        ) {
            if (record.rawRecord.is_recurring) {
                const recurrenceUpdatePolicy = await this.askRecurrenceUpdatePolicy();
                if (recurrenceUpdatePolicy !== "one") {
                    await this.orm.call("calendar.timeslot", "mass_delete", [record.id, recurrenceUpdatePolicy]);
                    return this.model.load();
                }
                super.deleteRecord(...arguments);
            } else {
                super.deleteRecord(...arguments);
            }
        } else {
            // Decline event
            this.orm
                .call("calendar.attendee_bis", "do_decline", [record.calendarAttendeeId])
                .then(this.model.load.bind(this.model));
        }
    }
}
