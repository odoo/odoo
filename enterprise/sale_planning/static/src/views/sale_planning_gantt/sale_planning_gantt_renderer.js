import { _t } from "@web/core/l10n/translation";
import { Domain } from "@web/core/domain";
import { patch } from "@web/core/utils/patch";
import { PlanningGanttRenderer } from "@planning/views/planning_gantt/planning_gantt_renderer";
import { useService } from "@web/core/utils/hooks";
import { renderToMarkup } from "@web/core/utils/render";
import { xml } from "@odoo/owl";
import { escape } from "@web/core/utils/strings";

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
        return Domain.and([
            domain,
            [['sale_line_id.state', '!=', 'cancel']],
            [["sale_line_id", "!=", false]]
        ]).toList({});
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
        const template = xml`
            <p class="o_view_nocontent_smiling_face">${escape(_t("No shifts found!"))}</p>
            <p>${escape(
                _t(
                    "Assign your sales orders to the right people based on their roles and availability."
                )
            )}</p>
        `;
        props.noContentHelp = renderToMarkup(template);
        props.onCreateEdit = () => {
            this.props.create(props.context);
        };
        return props;
    },
    displayFailedPlanningNotification(message) {
        return this.notification.add(message, { type: "danger" });
    },
    openPlanDialogCallback(result) {
        if (!result) {
            this.displayFailedPlanningNotification(
                _t("This resource is not available for this shift during the selected period.")
            );
        }
    },
    /**
     * @override
     */
    async onPlan(rowId, columnStart, columnStop) {
        const { start, stop } = this.getColumnStartStop(columnStart, columnStop);
        const schedule = this.props.model.getDialogContext({ rowId, start, stop });
        if ("sale_line_id" in schedule) {
            if (!schedule.sale_line_id) {
                this.displayFailedPlanningNotification(
                    _t("There are no sales order items to plan.")
                );
            } else {
                const slotIds = await this.props.model.searchShiftsToPlan(
                    [
                        ["sale_line_id", "=", schedule.sale_line_id],
                        ["start_datetime", "=", false],
                        ["end_datetime", "=", false],
                    ],
                    false
                );
                if (slotIds.length) {
                    await this.props.model.reschedule(slotIds, schedule, false);
                } else {
                    this.displayFailedPlanningNotification(
                        _t(
                            "There are no hours left to plan, or there are no resources available at the time."
                        )
                    );
                }
            }
            return;
        }
        const currentRow = this.rows.find((row) => row.id === rowId);
        this.roleIds = (currentRow.progressBar && currentRow.progressBar.role_ids) || [];
        const existsShiftToPlan = await this.props.model.searchShiftsToPlan(
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
    /**
     * @override
     */
    getPopoverProps(pill) {
        const popoverProps = super.getPopoverProps(pill);
        const { record } = pill;
        if (record.sale_line_plannable && this.isPlanningManager) {
            const deleteBtnIndex = popoverProps.buttons.findIndex((btn) => btn.class.includes("btn-delete"));
            const unscheduleBtn = {
                text: _t("Unschedule"),
                class: "btn btn-secondary",
                onClick: async () => {
                    await this.model.orm.call(this.model.metaData.resModel, "action_unschedule", [record.id]);
                    await this.model.fetchData(this.model.searchParams);
                },
            };

            if (deleteBtnIndex === -1) {
                popoverProps.buttons.push(unscheduleBtn);
            } else {
                popoverProps.buttons.splice(deleteBtnIndex, 0, unscheduleBtn);
            }
        }
        return popoverProps;
    },
});
