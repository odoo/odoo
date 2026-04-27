import { SelectCreateAutoPlanDialog } from "@project_enterprise/views/view_dialogs/select_auto_plan_create_dialog";
import { _t } from "@web/core/l10n/translation";
import { Avatar } from "@mail/views/web/fields/avatar/avatar";
import { markup, onWillUnmount, useEffect } from "@odoo/owl";
import { localization } from "@web/core/l10n/localization";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";
import { GanttRenderer } from "@web_gantt/gantt_renderer";
import { escape } from "@web/core/utils/strings";
import { MilestonesPopover } from "./milestones_popover";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { formatFloatTime } from "@web/views/fields/formatters";

export class TaskGanttRenderer extends GanttRenderer {
    static components = {
        ...GanttRenderer.components,
        Avatar,
    };
    static headerTemplate = "project_enterprise.TaskGanttRenderer.Header";
    static rowHeaderTemplate = "project_enterprise.TaskGanttRenderer.RowHeader";
    static rowContentTemplate = "project_enterprise.TaskGanttRenderer.RowContent";
    static totalRowTemplate = "project_enterprise.TaskGanttRenderer.TotalRow";
    static pillTemplate = "project_enterprise.TaskGanttRenderer.Pill";
    setup() {
        super.setup(...arguments);
        this.notificationService = useService("notification");
        this.orm = useService("orm");
        useEffect(
            (el) => el.classList.add("o_project_gantt"),
            () => [this.gridRef.el]
        );
        const position = localization.direction === "rtl" ? "bottom" : "right";
        this.milestonePopover = usePopover(MilestonesPopover, { position });
        onWillUnmount(() => {
            this.notificationFn?.();
        });
    }

    /**
     * @override
     */
    enrichPill(pill) {
        const enrichedPill = super.enrichPill(pill);
        if (enrichedPill?.record) {
            if (
                this.props.model.highlightIds &&
                !this.props.model.highlightIds.includes(enrichedPill.record.id)
            ) {
                pill.className += " opacity-25";
            }
        }
        return enrichedPill;
    }

    computeVisibleColumns() {
        super.computeVisibleColumns();
        this.columnMilestones = {}; // deadlines and milestones by project
        for (const column of this.columns) {
            this.columnMilestones[column.id] = {
                hasDeadLineExceeded: false,
                allReached: true,
                projects: {},
                hasMilestone: false,
                hasDeadline: false,
                hasStartDate: false,
            };
        }
        // Handle start date at the beginning of the current period
        this.columnMilestones[this.columns[0].id].edge = {
            projects: {},
            hasStartDate: false,
        };
        const projectStartDates = [...this.model.data.projectStartDates];
        const projectDeadlines = [...this.model.data.projectDeadlines];
        const milestones = [...this.model.data.milestones];

        let project = projectStartDates.shift();
        let projectDeadline = projectDeadlines.shift();
        let milestone = milestones.shift();
        let i = 0;
        while (i < this.columns.length && (project || projectDeadline || milestone)) {
            const column = this.columns[i];
            const nextColumn = this.columns[i + 1];
            const info = this.columnMilestones[column.id];

            if (i == 0 && project && column && column.stop > project.date) {
                // For the first column, start dates have to be displayed at the start of the period
                if (!info.edge.projects[project.id]) {
                    info.edge.projects[project.id] = {
                        milestones: [],
                        id: project.id,
                        name: project.name,
                    };
                }
                info.edge.projects[project.id].isStartDate = true;
                info.edge.hasStartDate = true;
                project = projectStartDates.shift();
            } else if (project && nextColumn?.stop > project.date) {
                if (!info.projects[project.id]) {
                    info.projects[project.id] = {
                        milestones: [],
                        id: project.id,
                        name: project.name,
                    };
                }
                info.projects[project.id].isStartDate = true;
                info.hasStartDate = true;
                project = projectStartDates.shift();
            }

            if (projectDeadline && column.stop > projectDeadline.date) {
                if (!info.projects[projectDeadline.id]) {
                    info.projects[projectDeadline.id] = {
                        milestones: [],
                        id: projectDeadline.id,
                        name: projectDeadline.name,
                    };
                }
                info.projects[projectDeadline.id].isDeadline = true;
                info.hasDeadline = true;
                projectDeadline = projectDeadlines.shift();
            }

            if (milestone && column.stop > milestone.deadline) {
                const [projectId, projectName] = milestone.project_id;
                if (!info.projects[projectId]) {
                    info.projects[projectId] = {
                        milestones: [],
                        id: projectId,
                        name: projectName,
                    };
                }
                const { is_deadline_exceeded, is_reached } = milestone;
                info.projects[projectId].milestones.push(milestone);
                info.hasMilestone = true;
                milestone = milestones.shift();
                if (is_deadline_exceeded) {
                    info.hasDeadLineExceeded = true;
                }
                if (!is_reached) {
                    info.allReached = false;
                }
            }
            if (
                (!project || !nextColumn || nextColumn?.stop < project.date) &&
                (!projectDeadline || column.stop < projectDeadline.date) &&
                (!milestone || column.stop < milestone.deadline)
            ) {
                i++;
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
        props.context.allocated_hours = formatFloatTime(props.context.allocated_hours);
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
        const onSelectedAutoPlan = (resIds) => {
            props.context.smart_task_scheduling = true;
            if (resIds.length) {
                this.model.reschedule(
                    resIds,
                    props.context,
                    this.openPlanDialogCallback.bind(this)
                );
            }
        };
        props.onSelectedNoSmartSchedule = props.onSelected;
        props.onSelected = onSelectedAutoPlan;
        props.onCreateEdit = onCreateEdit;
        return props;
    }

    hasAvatar(row) {
        return row.id in this.rowsWithAvatar;
    }

    getNotificationOnSmartSchedule(warningString, old_vals_per_task_id) {
        this.notificationFn?.();
        this.notificationFn = this.notificationService.add(
            markup(
                `<i class="fa btn-link fa-check"></i><span class="ms-1">${escape(
                    warningString
                )}</span>`
            ),
            {
                type: "success",
                sticky: true,
                buttons: [
                    {
                        name: "Undo",
                        icon: "fa-undo",
                        onClick: async () => {
                            const ids = Object.keys(old_vals_per_task_id).map(Number);
                            await this.orm.call("project.task", "action_rollback_auto_scheduling", [
                                ids,
                                old_vals_per_task_id,
                            ]);
                            this.model.toggleHighlightPlannedFilter(false);
                            this.notificationFn();
                            await this.model.fetchData();
                        },
                    },
                ],
            }
        );
    }

    openPlanDialogCallback(res) {
        if (res && Array.isArray(res)) {
            const warnings = Object.entries(res[0]);
            const old_vals_per_task_id = res[1];
            for (const warning of warnings) {
                this.notificationService.add(warning[1], {
                    title: _t("Warning"),
                    type: "warning",
                    sticky: true,
                });
            }
            if (warnings.length === 0) {
                this.getNotificationOnSmartSchedule(
                    _t("Tasks have been successfully scheduled for the upcoming periods."),
                    old_vals_per_task_id
                );
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

    onPlan(rowId, columnStart, columnStop) {
        const { start, stop } = this.getColumnStartStop(columnStart, columnStop);
        this.dialogService.add(
            SelectCreateAutoPlanDialog,
            this.getSelectCreateDialogProps({ rowId, start, stop, withDefault: true })
        );
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    onMilestoneMouseEnter(ev, projects) {
        this.milestonePopover.open(ev.target, {
            displayMilestoneDates: this.model.metaData.scale.id === "year",
            displayProjectName: !this.model.searchParams.context.default_project_id,
            projects,
        });
    }

    onMilestoneMouseLeave() {
        this.milestonePopover.close();
    }
}
