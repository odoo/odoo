import { registry } from "@web/core/registry";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { CalendarFormView } from "./calendar_form_view";
import { CalendarFormController } from "./calendar_form_controller";
import { serializeDate, serializeDateTime } from "@web/core/l10n/dates";

export const QUICK_CREATE_CALENDAR_EVENT_FIELDS = {
    name: { type: "string" },
    start: { type: "datetime" },
    start_date: { type: "date" },
    stop_date: { type: "date" },
    stop: { type: "datetime" },
    allday: { type: "boolean" },
    partner_ids: { type: "many2many" },
    privacy: { type: "selection" },
    location: { type: "string" },
    videocall_location: { type: "string" },
    notes: { type: "string" }
};

function getDefaultValuesFromRecord(data) {
    const context = {};
    for (const fieldName in QUICK_CREATE_CALENDAR_EVENT_FIELDS) {
        if (fieldName in data) {
            let value = data[fieldName];
            const { type } = QUICK_CREATE_CALENDAR_EVENT_FIELDS[fieldName]
            if (type === 'many2many') {
                value = value.records.map((record) => record.resId);
            } else if (type === 'date') {
                value = value && serializeDate(value);
            } else if (type === "datetime") {
                value = value && serializeDateTime(value);
            }
            context[`default_${fieldName}`] = value || false;
        }
    }
    return context;
}

export class CalendarQuickCreateFormController extends CalendarFormController {

    goToFullEvent() {
        const context = getDefaultValuesFromRecord(this.model.root.data);
        return this.actionService.doAction(
            {
                type: "ir.actions.act_window",
                res_model: "calendar.event",
                views: [[false, "form"]],
                res_id: this.model.root.resId || false,
            },
            {
                additionalContext: {
                    ...this.props.context,
                    ...context,
                },
            }
        );
    }

    /**
     * This override makes it so that, after creating a calendar event through the activity buttons/widget
     * on a record, the user is redirected back to the record they clicked the activity button on.
     */
    async onRecordSaved() {
        await super.onRecordSaved(arguments);
        if (this.props.context.return_to_parent_breadcrumb) {
            const breadcrumb = this.actionService.currentController.config.breadcrumbs.at(-2);
            if (breadcrumb) {
                // todo guce postfreeze: make safer (knowledge macro system?)
                breadcrumb.onSelected();
            }
        }
    }
}

registry.category("views").add("calendar_quick_create_form_view", {
    ...CalendarFormView,
    Controller: CalendarQuickCreateFormController,
});

export class CalendarQuickCreate extends FormViewDialog {

    setup() {
        super.setup();
        Object.assign(this.viewProps, {
            ...this.viewProps,
            buttonTemplate: "calendar.CalendarQuickCreateButtons",
        });
    }
}
