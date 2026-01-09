import { registry } from "@web/core/registry";
import { dateRangeField } from "@web/views/fields/datetime/datetime_field";
import { useEffect, useState } from "@odoo/owl";
import { Field } from "@web/views/fields/field";
import { usePopover } from "@web/core/popover/popover_hook";
import { HourTimeSelectionPopover } from "./hour_time_selection_popover";

function hoursMinutesToFloat(hours, minutes) {
    return Number(hours) + Number(minutes) / 60;
}

function timeValuesFromParts(hours, minutes) {
    return timeValuesFromFloat(hoursMinutesToFloat(hours, minutes));
}

function timeValuesFromFloat(floatValue) {
    const hours = Math.floor(floatValue);
    const minutes = Math.round((floatValue - hours) * 60);
    return {
        hours: String(hours).padStart(2, "0"),
        minutes: String(minutes).padStart(2, "0"),
        floatValue: floatValue,
    };
}

function parseTimeInput(value) {
    const [hoursPart, minutesPart] = value.split(":");
    return timeValuesFromParts(Number(hoursPart), Number(minutesPart));
}

export class HrHolidaysDateRangeField extends dateRangeField.component {
    static template = "hr_holidays.HrHolidaysDateRangeField";
    static components = {
        Field,
    };

    static props = {
        ...dateRangeField.component.props,
        startPeriodField: { type: String, optional: true },
        endPeriodField: { type: String, optional: true },
        hourFromField: { optional: true },
        hourToField: { optional: true },
    };

    setup() {
        super.setup();
        this.leaveType = useState({
            request_unit: this.props.record.data.leave_type_request_unit,
        });
        this.popover = usePopover(HourTimeSelectionPopover, {
            onClose: this.onClose.bind(this),
        });
        this.timeValues = useState({
            hours: "00",
            minutes: "00",
            floatValue: 0,
        });

        useEffect(
            () => {
                this.leaveType.request_unit = this.props.record.data.leave_type_request_unit;
            },
            () => [this.props.record.data.leave_type_request_unit]
        );
    }

    onCharHoursClick(ev, fieldName) {
        ev.preventDefault();
        const anchor = ev.target;
        this.activeHourField = fieldName;
        this.activeHourAnchor = anchor;
        const parsedValues = parseTimeInput(anchor.value);
        this.setTimeValues(parsedValues || timeValuesFromFloat(this.getHourValue(fieldName)));
        this.popover.open(anchor, {
            timeValues: this.timeValues,
            onTimeChange: this.onTimeChange.bind(this),
        });
        anchor?.focus();
    }

    onTimeChange(newTimeValues) {
        const normalizedValues = timeValuesFromParts(
            Number(newTimeValues.hours),
            Number(newTimeValues.minutes)
        );
        this.setTimeValues(normalizedValues);
        if (this.activeHourAnchor && "value" in this.activeHourAnchor) {
            this.activeHourAnchor.value = `${normalizedValues.hours}:${normalizedValues.minutes}`;
        }
    }

    onClose() {
        this.props.record.update({ [this.activeHourField]: this.timeValues.floatValue });
    }

    getHourValue(fieldName) {
        const value = fieldName ? this.props.record.data[fieldName] : 0;
        return Number.isFinite(Number(value)) ? Number(value) : 0;
    }

    setTimeValues(timeValues) {
        this.timeValues.hours = timeValues.hours;
        this.timeValues.minutes = timeValues.minutes;
        this.timeValues.floatValue = timeValues.floatValue;
    }
}

const START_PERIOD = "start_period_field";
const END_PERIOD = "end_period_field";
const HOUR_FROM = "hour_from_field";
const HOUR_TO = "hour_to_field";

export const hrHolidaysDateRangeField = {
    ...dateRangeField,
    component: HrHolidaysDateRangeField,
    supportedOptions: [
        ...dateRangeField.supportedOptions,
        { name: START_PERIOD, type: "field" },
        { name: END_PERIOD, type: "field" },
        { name: HOUR_FROM, type: "field" },
        { name: HOUR_TO, type: "field" },
    ],
    extractProps: ({ attrs, options, placeholder, type }, dynamicInfo) => {
        const base = dateRangeField.extractProps(
            { attrs, options, placeholder, type },
            dynamicInfo
        );

        return {
            ...base,
            startPeriodField: options[START_PERIOD],
            endPeriodField: options[END_PERIOD],
            hourFromField: options[HOUR_FROM],
            hourToField: options[HOUR_TO],
        };
    },
};

registry.category("fields").add("hr_holidays_daterange", hrHolidaysDateRangeField);
