import { _t } from "@web/core/l10n/translation";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { GanttController } from "@web_gantt/gantt_controller";
import { usePlanningControllerActions } from "../planning_hooks";
import { serializeDateTime } from "@web/core/l10n/dates";
import { Domain } from "@web/core/domain";
import { localEndOf, localStartOf } from "@web_gantt/gantt_helpers";

const { DateTime } = luxon;

export class PlanningGanttController extends GanttController {
    static components = {
        ...GanttController.components,
        Dropdown,
        DropdownItem,
    }
    /**
     * @override
     */
    setup() {
        super.setup();
        this.planningControllerActions = usePlanningControllerActions({
            getAdditionalContext: () => this.model.getAdditionalContext(),
            getDomain: () => {
                const { dateStartField, dateStopField, scale } = this.model.metaData;
                const focusDate = this.getCurrentFocusDate();
                const start = localStartOf(focusDate, scale.unit);
                const stop = localEndOf(focusDate, scale.unit);
                const domain = Domain.and([
                    this.model.searchParams.domain,
                    [
                        "&",
                        [dateStartField, "<", serializeDateTime(stop)],
                        [dateStopField, ">", serializeDateTime(start)],
                    ],
                ]);
                return domain.toList();
            },
            getRecords: () => {
                if (this.model.useSampleModel) {
                    return [];
                }
                return this.model.data.records;
            },
            getResModel: () => this.model.metaData.resModel,
            getStartDate: () => {
                const { scale } = this.model.metaData;
                const focusDate = this.getCurrentFocusDate();
                return localStartOf(focusDate, scale.unit);
            },
            toggleHighlightPlannedFilter: (highlightPlannedIds) => this.env.searchModel.toggleHighlightPlannedFilter(highlightPlannedIds),
            reload: () => this.model.fetchData(),
        });
    }

    /**
     * @override
     */
    onAddClicked() {
        const { scale, globalStart, globalStop } = this.model.metaData;
        const today = DateTime.local().startOf("day");
        if (scale.id !== "day" && globalStart <= today.endOf("day") && today <= globalStop) {
            let start = today;
            let stop = today.endOf(scale.interval);
            const context = this.model.getDialogContext({ start, stop, withDefault: true });
            this.create(context);
            return;
        }
        super.onAddClicked(...arguments);
    }

    /**
     * @override
     */
    openDialog(props, options) {
        const record = this.model.data.records.find((r) => r.id === props.resId);
        const title = record ? record.display_name : _t("Add Shift");
        const context = {
            ...props.context,
            my_planning_action: this.props.context.my_planning_action,
            is_record_created: !record,
            view_start_date: serializeDateTime(this.model.metaData.globalStart),
            view_end_date: serializeDateTime(this.model.metaData.globalStop),
        };
        super.openDialog({ ...props, title, context }, options);
    }
}
