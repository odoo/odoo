import { Component, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { computeM2OProps, Many2One } from "@web/views/fields/many2one/many2one";
import { buildM2OFieldDescription, many2OneFieldProps } from "@web/views/fields/many2one/many2one_field";
import { formatPercentage } from "@web/views/fields/formatters";

const RESOURCE_CALENDAR_SPECIFICATION = {
    work_time_rate: {},
    calendar_type: {},
    attendance_ids: {
        fields: {
            dayofweek: {},
            date: {},
            duration_hours: {},
        },
    },
};

export class Many2OneResourceCalendarField extends Component {
    static template = "resource.Many2OneResourceCalendarField";
    static components = { Many2One };
    props = useProps(many2OneFieldProps);

    get m2oProps() {
        return {
            ...computeM2OProps(this.props),
            specification: RESOURCE_CALENDAR_SPECIFICATION,
        };
    }

    formatWorkTimeRate(record) {
        return formatPercentage(record.work_time_rate);
    }

    formatHours(hours) {
        return hours % 1 === 0 ? String(hours) : hours.toFixed(1);
    }

    getSchedulePreview(record) {
        const attendances = record.attendance_ids || [];
        if (record.calendar_type === "variable") {
            const days = new Set();
            let hours = 0;
            for (const attendance of attendances) {
                if (attendance.date) {
                    days.add(attendance.date);
                }
                hours += attendance.duration_hours;
            }
            return _t("Variable (%(days)s %(dayLabel)s - %(hours)sh)", {
                days: days.size,
                dayLabel: days.size === 1 ? _t("day") : _t("days"),
                hours: this.formatHours(hours),
            });
        }
        const hoursByDay = [0, 0, 0, 0, 0, 0, 0];
        for (const attendance of attendances) {
            if (attendance.date) {
                continue;
            }
            hoursByDay[Number(attendance.dayofweek)] += attendance.duration_hours;
        }
        return hoursByDay.map((hours) => this.formatHours(hours)).join(" - ");
    }
}

export const many2OneResourceCalendarField = buildM2OFieldDescription(Many2OneResourceCalendarField);

registry.category("fields").add("resource_calendar_many2one", many2OneResourceCalendarField);
