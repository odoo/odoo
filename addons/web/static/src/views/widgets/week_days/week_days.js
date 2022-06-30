/** @odoo-module **/

import { registry } from "@web/core/registry";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { localization } from "@web/core/l10n/localization";

const { Component } = owl;

const WEEKDAYS = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"];

export class WeekDays extends Component {
    get weekdays() {
        return [
            ...WEEKDAYS.slice(localization.weekStart % WEEKDAYS.length, WEEKDAYS.length),
            ...WEEKDAYS.slice(0, localization.weekStart % WEEKDAYS.length),
        ];
    }
    get data() {
        return Object.fromEntries(this.weekdays.map((day) => [day, this.props.record.data[day]]));
    }

    onChange(day, checked) {
        this.props.record.update({ [day]: checked });
    }
}

WeekDays.template = "web.WeekDays";
WeekDays.components = { CheckBox };

WeekDays.fieldDependencies = {
    sun: { type: "boolean" },
    mon: { type: "boolean" },
    tue: { type: "boolean" },
    wed: { type: "boolean" },
    thu: { type: "boolean" },
    fri: { type: "boolean" },
    sat: { type: "boolean" },
};

registry.category("view_widgets").add("week_days", WeekDays);
