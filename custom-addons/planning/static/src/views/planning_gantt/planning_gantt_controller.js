/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { GanttController } from "@web_gantt/gantt_controller";
import { usePlanningControllerActions } from "../planning_hooks";

const { DateTime } = luxon;

export class PlanningGanttController extends GanttController {
    /**
     * @override
     */
    setup() {
        super.setup();
        this.planningControllerActions = usePlanningControllerActions({
            getAdditionalContext: () => this.model.getAdditionalContext(),
            getDomain: () => this.model.getDomain(),
            getRecords: () => {
                if (this.model.useSampleModel) {
                    return [];
                }
                return this.model.data.records;
            },
            getResModel: () => this.model.metaData.resModel,
            getStartDate: () => this.model.metaData.startDate,
            toggleHighlightPlannedFilter: (highlightPlannedIds) => this.env.searchModel.toggleHighlightPlannedFilter(highlightPlannedIds),
            reload: () => this.model.fetchData(),
        });
    }

    /**
     * @override
     */
    onAddClicked() {
        const { scale, startDate, stopDate } = this.model.metaData;
        const today = DateTime.local().startOf("day");
        if (scale.id !== "day" && startDate <= today.endOf("day") && today <= stopDate) {
            let start = today;
            let stop;
            if (["week", "month"].includes(scale.id)) {
                start = today.set({ hours: 8, minutes: 0, seconds: 0 });
                stop = today.set({ hours: 17, minutes: 0, seconds: 0 });
            } else {
                stop = today.endOf(scale.interval);
            }
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
        super.openDialog({ ...props, title }, options);
    }
}
