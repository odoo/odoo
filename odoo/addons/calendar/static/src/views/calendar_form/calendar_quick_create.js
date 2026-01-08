/** @odoo-module **/

import { registry } from "@web/core/registry";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { CalendarFormView } from "./calendar_form_view";
import { CalendarFormController } from "./calendar_form_controller";
import { serializeDate, serializeDateTime } from "@web/core/l10n/dates";

const QUICK_CREATE_CALENDAR_EVENT_FIELDS = {
    name: { type: "string" },
    start: { type: "datetime" },
    start_date: { type: "date" },
    stop_date: { type: "date" },
    stop: { type: "datetime" },
    allday: { type: "boolean" },
    partner_ids: { type: "many2many" },
    videocall_location: { type: "string" },
    description: { type: "string" }
};

function getDefaultValuesFromRecord(data) {
    const context = {};
    for (let fieldName in QUICK_CREATE_CALENDAR_EVENT_FIELDS) {
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
    static props = {
        ...CalendarFormController.props,
        goToFullEvent: Function,
    };

    goToFullEvent() {
        const context = getDefaultValuesFromRecord(this.model.root.data)
        this.props.goToFullEvent(context);
    }
}

registry.category("views").add("calendar_quick_create_form_view", {
    ...CalendarFormView,
    Controller: CalendarQuickCreateFormController,
});

export class CalendarQuickCreate extends FormViewDialog {
    static props = {
        ...FormViewDialog.props,
        goToFullEvent: Function,
    };

    setup() {
        super.setup();
        Object.assign(this.viewProps, {
            ...this.viewProps,
            buttonTemplate: "calendar.CalendarQuickCreateButtons",
            goToFullEvent: (contextData) => {
                this.props.goToFullEvent(contextData);
            }
        });
    }
}
