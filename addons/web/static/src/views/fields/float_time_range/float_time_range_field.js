import { Component } from "@odoo/owl";
import { parseFloatTime } from "@web/views/fields/parsers";
import { formatFloatTime } from "@web/views/fields/formatters";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "../standard_field_props";

const { DateTime } = luxon;

// Converts the time value using the server timezone
const serializeTime = (value, format) => {
    const dt = DateTime.fromFormat(value, format);
    return dt.setZone("utc").toFormat(format);
};

// Converts the time value coming from the server to the local timezone
const deserializeTime = (value, format) => {
    const dt = DateTime.fromFormat(value, format, { zone: "utc" });
    return dt.toLocal().toFormat(format);
};

export class TimeRangeField extends Component {
    static props = {
        ...standardFieldProps,
        endDateField: { type: String, optional: true },
        startDateField: { type: String, optional: true },
    };
    static template = "web.TimeRangeField";

    setup() {
        const relatedField = this.props.startDateField || this.props.endDateField;
        this.field = this.props.record.fields[this.props.name];
        this.startDateField = this.props.startDateField || this.props.name;
        this.endDateField = relatedField ? this.props.endDateField || this.props.name : null;
    }

    getFormattedValue(valueIndex) {
        const value = this.getRecordValue()[valueIndex];
        return deserializeTime(formatFloatTime(value), "HH:mm");
    }

    getRecordValue() {
        return [
            this.props.record.data[this.startDateField],
            this.props.record.data[this.endDateField],
        ];
    }

    onChange(value, fieldName) {
        const parsedValue = value ? parseFloatTime(serializeTime(value, "HH:mm")) : false;
        this.props.record.update({ [fieldName]: parsedValue }, { save: this.props.readonly });
    }
}

const START_TIME_FIELD_OPTION = "start_time_field";
const END_TIME_FIELD_OPTION = "end_time_field";

export const timeRangeField = {
    component: TimeRangeField,
    displayName: _t("Time Range"),
    supportedOptions: [
        {
            label: _t("Start time field"),
            name: START_TIME_FIELD_OPTION,
            type: "field",
            availableTypes: ["float"],
        },
        {
            label: _t("End time field"),
            name: END_TIME_FIELD_OPTION,
            type: "field",
            availableTypes: ["float"],
        },
    ],
    supportedTypes: ["float"],
    extractProps: ({ attrs, options }) => ({
        endDateField: options[END_TIME_FIELD_OPTION],
        startDateField: options[START_TIME_FIELD_OPTION],
    }),
    fieldDependencies: ({ type, attrs, options }) => {
        const deps = [];
        if (options[START_TIME_FIELD_OPTION]) {
            deps.push({
                name: options[START_TIME_FIELD_OPTION],
                type,
                readonly: false,
                ...attrs,
            });
            if (options[END_TIME_FIELD_OPTION]) {
                console.warn(
                    `A field cannot have both ${START_TIME_FIELD_OPTION} and ${END_TIME_FIELD_OPTION} options at the same time`
                );
            }
        } else if (options[END_TIME_FIELD_OPTION]) {
            deps.push({
                name: options[END_TIME_FIELD_OPTION],
                type,
                readonly: false,
                ...attrs,
            });
        }
        return deps;
    },
};

registry.category("fields").add("float_time_range", timeRangeField);
