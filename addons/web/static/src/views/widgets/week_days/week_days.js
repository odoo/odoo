// @ts-check

/** @module @web/views/widgets/week_days/week_days - Widget rendering seven day-of-week checkboxes respecting the locale's week start day */

import { Component } from "@odoo/owl";
import { CheckBox } from "@web/components/checkbox/checkbox";
import { localization } from "@web/core/l10n/localization";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
const WEEKDAYS = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"];

/** Widget rendering a row of seven day-of-week checkboxes (sun-sat), respecting the locale's week start day. */
export class WeekDays extends Component {
    static template = "web.WeekDays";
    static components = { CheckBox };
    static props = {
        record: Object,
        readonly: Boolean,
    };

    /** @returns {string[]} day abbreviations rotated to start on the locale's first day of the week */
    get weekdays() {
        return [
            ...WEEKDAYS.slice(
                localization.weekStart % WEEKDAYS.length,
                WEEKDAYS.length,
            ),
            ...WEEKDAYS.slice(0, localization.weekStart % WEEKDAYS.length),
        ];
    }
    /** @returns {Record<string, boolean>} map of day abbreviations to their checked state */
    get data() {
        return Object.fromEntries(
            this.weekdays.map((day) => [day, this.props.record.data[day]]),
        );
    }

    /**
     * @param {string} day - day abbreviation (e.g. "mon")
     * @param {boolean} checked
     */
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
