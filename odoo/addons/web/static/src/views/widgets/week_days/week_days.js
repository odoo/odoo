/** @odoo-module **/

import { registry } from "@web/core/registry";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { localization } from "@web/core/l10n/localization";
import { _t } from "@web/core/l10n/translation";

import { Component } from "@odoo/owl";

const WEEKDAYS = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"];

export class WeekDays extends Component {
    static template = "web.WeekDays";
    static components = { CheckBox };

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

export const weekDays = {
    component: WeekDays,
    fieldDependencies: [
        { name: "sun", type: "boolean", string: _t("Sun"), readonly: false },
        { name: "mon", type: "boolean", string: _t("Mon"), readonly: false },
        { name: "tue", type: "boolean", string: _t("Tue"), readonly: false },
        { name: "wed", type: "boolean", string: _t("Wed"), readonly: false },
        { name: "thu", type: "boolean", string: _t("Thu"), readonly: false },
        { name: "fri", type: "boolean", string: _t("Fri"), readonly: false },
        { name: "sat", type: "boolean", string: _t("Sat"), readonly: false },
    ],
};

registry.category("view_widgets").add("week_days", weekDays);
