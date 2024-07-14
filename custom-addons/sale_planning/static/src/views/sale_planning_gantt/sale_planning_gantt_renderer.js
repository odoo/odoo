/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Domain } from "@web/core/domain";
import { patch } from "@web/core/utils/patch";
import { PlanningGanttRenderer } from "@planning/views/planning_gantt/planning_gantt_renderer";
import { useService } from "@web/core/utils/hooks";

patch(PlanningGanttRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        this.notification = useService("notification");
        this.roleIds = [];
    },
    getPlanDialogDomain() {
        let domain = super.getPlanDialogDomain(...arguments);
        if (this.roleIds.length) {
            domain = Domain.and([domain, [['role_id', 'in', this.roleIds]]]);
        }
        return Domain.and([domain, [["sale_line_id", "!=", false]]]).toList({});
    },
    getSelectCreateDialogProps() {
        const props = super.getSelectCreateDialogProps(...arguments);
        this.model.addSpecialKeys(props.context);
        Object.assign(props.context, {
            default_start_datetime: props.context.start_datetime,
            default_end_datetime: props.context.end_datetime,
            search_default_group_by_resource: false,
            search_default_group_by_role: false,
            search_default_role_id: props.context.role_id || false,
            search_default_project_id: props.context.project_id || false,
            planning_slots_to_schedule: true,
            search_default_sale_order_id:
            props.context.planning_gantt_active_sale_order_id || null,
        });
        return props;
    },
    openPlanDialogCallback(result) {
        if (!result) {
            this.notification.add(
                _t("This resource is not available for this shift during the selected period."),
                { type: "danger" }
            );
        }
    },
    /**
     * @override
     */
    async onPlan(rowId, columnStart, columnStop) {
        const currentRow = this.rows.find((row) => row.id === rowId);
        this.roleIds = (currentRow.progressBar && currentRow.progressBar.role_ids) || [];
        const existsShiftToPlan = await this.props.model.existsShiftToPlan(
            this.getPlanDialogDomain()
        );
        if (this.model.useSampleModel) {
            rowId = false;
        }
        if (!existsShiftToPlan) {
            return this.onCreate(rowId, columnStart, columnStop);
        }
        super.onPlan(rowId, columnStart, columnStop);
    },
});
