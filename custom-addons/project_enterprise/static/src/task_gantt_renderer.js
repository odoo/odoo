/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Avatar } from "@mail/views/web/fields/avatar/avatar";
import { markup, useEffect } from "@odoo/owl";
import { localization } from "@web/core/l10n/localization";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";
import { GanttRenderer } from "@web_gantt/gantt_renderer";
import { escape } from "@web/core/utils/strings";
import { MilestonesPopover } from "./milestones_popover";
import { TaskGanttPopover } from "./task_gantt_popover";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";

export class TaskGanttRenderer extends GanttRenderer {
    setup() {
        super.setup(...arguments);
        this.notificationService = useService("notification");
        useEffect(
            (el) => el.classList.add("o_project_gantt"),
            () => [this.rootRef.el]
        );
        const position = localization.direction === "rtl" ? "bottom" : "right";
        this.milestonePopover = usePopover(MilestonesPopover, { position });
    }

    computeColumns() {
        super.computeColumns();
        this.columnMilestones = {};
        for (const column of this.columns) {
            this.columnMilestones[column.id] = {
                hasDeadLineExceeded: false,
                allReached: true,
                milestones: [],
            };
        }
        let index = 0;
        for (const m of this.model.data.milestones) {
            const { is_deadline_exceeded, is_reached } = m;
            for (let i = index; i < this.columns.length ; i++) {
                const column = this.columns[i];
                if (column.stop < m.deadline) {
                    index++;
                    continue;
                } else {
                    const info = this.columnMilestones[column.id];
                    info.milestones.push(m);
                    if (is_deadline_exceeded) {
                        info.hasDeadLineExceeded = true;
                    }
                    if (!is_reached) {
                        info.allReached = false;
                    }
                    break;
                }
            }
        }
    }

    computeDerivedParams() {
        this.rowsWithAvatar = {};
        super.computeDerivedParams();
    }

    getConnectorAlert(masterRecord, slaveRecord) {
        if (
            masterRecord.display_warning_dependency_in_gantt &&
            slaveRecord.display_warning_dependency_in_gantt
        ) {
            return super.getConnectorAlert(...arguments);
        }
    }

    getPopoverProps(pill) {
        const props = super.getPopoverProps(...arguments);
        const { record } = pill;
        if (record.planning_overlap) {
            props.context.planningOverlapHtml = markup(record.planning_overlap);
        }
        props.unschedule = async () => {
            await this.model.unscheduleTask(record.id);
        }

        return props;
    }

    getAvatarProps(row) {
        return this.rowsWithAvatar[row.id];
    }

    getSelectCreateDialogProps() {
        const props = super.getSelectCreateDialogProps(...arguments);
        const onCreateEdit = () => {
            this.dialogService.add(FormViewDialog, {
                context: props.context,
                resModel: props.resModel,
                onRecordSaved: async (record) => {
                    await record.save({ reload: false });
                    await this.model.fetchData();
                },
            });
        };
        props.onCreateEdit = onCreateEdit;
        props.context.smart_task_scheduling = true;
        return props;
    }

    hasAvatar(row) {
        return row.id in this.rowsWithAvatar;
    }

    openPlanDialogCallback(res) {
        if (!res) {
            return;
        }
        for (const [warningType, warningString] of Object.entries(res)) {
            if (warningType === "out_of_scale_notification") {
                this.notificationService.add(
                    markup(
                        `<i class="fa btn-link fa-check"></i><span class="ms-1">${escape(
                            warningString
                        )}</span>`
                    ),
                    {
                        type: "success",
                    }
                );
            } else {
                this.notificationService.add(warningString, {
                    title: _t("Warning"),
                    type: "warning",
                    sticky: true,
                });
            }
        }
    }

    processRow(row) {
        const { groupedByField, name, resId } = row;
        if (groupedByField === "user_ids" && Boolean(resId)) {
            const { fields } = this.model.metaData;
            const resModel = fields.user_ids.relation;
            this.rowsWithAvatar[row.id] = { resModel, resId, displayName: name };
        }
        return super.processRow(...arguments);
    }

    shouldRenderRecordConnectors(record) {
        if (record.allow_task_dependencies) {
            return super.shouldRenderRecordConnectors(...arguments);
        }
        return false;
    }

    highlightPill(pillId, highlighted) {
        if (!this.connectorDragState.dragging) {
            return super.highlightPill(pillId, highlighted);
        }
        const pill = this.pills[pillId];
        if (!pill) {
            return;
        }
        const { record } = pill;
        if (!this.shouldRenderRecordConnectors(record)) {
            return super.highlightPill(pillId, false);
        }
        return super.highlightPill(pillId, highlighted);
    }


    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    onMilestoneMouseEnter(ev, milestones) {
        this.milestonePopover.open(ev.target, {
            milestones,
            displayMilestoneDates: this.model.metaData.scale.id === "year",
            displayProjectName: !this.model.searchParams.context.default_project_id,
        });
    }

    onMilestoneMouseLeave() {
        this.milestonePopover.close();
    }
}
TaskGanttRenderer.components = {
    ...GanttRenderer.components,
    Avatar,
    Popover: TaskGanttPopover,
};
TaskGanttRenderer.headerTemplate = "project_enterprise.TaskGanttRenderer.Header";
TaskGanttRenderer.rowHeaderTemplate = "project_enterprise.TaskGanttRenderer.RowHeader";
TaskGanttRenderer.rowContentTemplate = "project_enterprise.TaskGanttRenderer.RowContent";
TaskGanttRenderer.totalRowTemplate = "project_enterprise.TaskGanttRenderer.TotalRow";
TaskGanttRenderer.pillTemplate = "project_enterprise.TaskGanttRenderer.Pill";
