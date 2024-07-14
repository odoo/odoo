/** @odoo-module **/

import { PlanningGanttModel } from "@planning/views/planning_gantt/planning_gantt_model";
import { patch } from "@web/core/utils/patch";
import { serializeDateTime } from "@web/core/l10n/dates";

const GROUPBY_COMBINATIONS = [
    "sale_line_id",
    "sale_line_id,department_id",
    "sale_line_id,resource_id",
    "sale_line_id,role_id",
];

patch(PlanningGanttModel.prototype, {
    async load(searchParams) {
        const groupBy = searchParams.groupBy.slice();
        const groupBySO = Boolean(searchParams.context.planning_groupby_sale_order);
        if (groupBySO && groupBy.length === 0) {
            groupBy.push("sale_line_id");
        }
        return super.load({ ...searchParams, groupBy });
    },
    addSpecialKeys(context) {
        const { focusDate, startDate, stopDate, scale } = this.metaData;
        Object.assign(context, {
            focus_date: serializeDateTime(focusDate),
            default_start_datetime: serializeDateTime(startDate),
            default_end_datetime: serializeDateTime(stopDate),
            scale: scale.id,
        });
    },
    _allowCreateEmptyGroups(groupedBy) {
        return super._allowCreateEmptyGroups(...arguments) || groupedBy.includes("sale_line_id");
    },
    _allowedEmptyGroups(groupedBy) {
        return super._allowedEmptyGroups(...arguments) || GROUPBY_COMBINATIONS.includes(groupedBy.join(","));
    },
    _getRescheduleContext() {
        const context = super._getRescheduleContext(...arguments);
        this.addSpecialKeys(context);
        return context;
    },
    async existsShiftToPlan(planDomain) {
        const domain = planDomain || [
            "|",
            [dateStartField, "=", false],
            [dateStopField, "=", false],
        ];
        const { dateStartField, dateStopField, resModel } = this.metaData;
        const result = await this.orm.searchCount(resModel, domain, {
            context: this.searchParams.context,
            limit: 1,
        });
        return Boolean(result);
    },
});
