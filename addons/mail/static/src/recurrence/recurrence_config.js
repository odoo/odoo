import { Component, t, useProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Field } from "@web/views/fields/field";
import { WeekDays, weekDays } from "@web/views/widgets/week_days/week_days";

export class RecurrenceWeekDays extends WeekDays {
    static template = "mail.RecurrenceWeekDays";
    onChange(day) {
        this.props.record.update({ [day]: !this.data[day] });
    }
}

export class RecurrenceConfigWidget extends Component {
    static template = "mail.RecurrenceConfig";
    static components = {
        Field,
        RecurrenceWeekDays,
    };

    props = useProps({
        record: t.object(),
        readonly: t.boolean().optional(false),
    });

    setup() {
        const toggleField = this.props.record.data.is_recurring_field_name;
        const validationRules = {
            rrule_type_ui: toggleField,
            rrule_type: "rrule_type_ui == 'custom'",
            month_by: "rrule_type_ui == 'monthly' or rrule_type == 'monthly'",
            day: "(rrule_type_ui == 'monthly' or rrule_type == 'monthly') and month_by == 'date'",
            byday: "(rrule_type_ui == 'monthly' or rrule_type == 'monthly') and month_by == 'day'",
            weekday:
                "(rrule_type_ui == 'monthly' or rrule_type == 'monthly') and month_by == 'day'",
            end_type: toggleField,
            count: toggleField,
            until: `(${toggleField}) and end_type == 'end_date'`,
        };

        for (const [fieldName, condition] of Object.entries(validationRules)) {
            if (!this.props.record.activeFields[fieldName]) {
                this.props.record.activeFields[fieldName] = {};
            }
            this.props.record.activeFields[fieldName].required = condition;
        }
    }

    get record() {
        return this.props.record;
    }

    get data() {
        return this.props.record.data;
    }

    get isReadonly() {
        return this.props.readonly || false;
    }
}

registry.category("view_widgets").add("recurrence_config", {
    component: RecurrenceConfigWidget,
    fieldDependencies: [
        ...weekDays.fieldDependencies,
        { name: "rrule_type_ui", type: "selection", readonly: false },
        { name: "interval", type: "integer", readonly: false },
        { name: "rrule_type", type: "selection", readonly: false },
        { name: "month_by", type: "selection", readonly: false },
        { name: "day", type: "integer", readonly: false },
        { name: "byday", type: "selection", readonly: false },
        { name: "weekday", type: "selection", readonly: false },
        { name: "end_type", type: "selection", readonly: false },
        { name: "count", type: "integer", readonly: false },
        { name: "until", type: "date", readonly: false },
        { name: "is_recurring_field_name", type: "char" },
    ],
});
