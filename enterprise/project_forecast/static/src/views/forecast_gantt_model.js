import { registry } from "@web/core/registry"
import { PlanningGanttModel } from "@planning/views/planning_gantt/planning_gantt_model";
import { PlanningGanttView } from "@planning/views/planning_gantt/planning_gantt_view";

const viewRegistry = registry.category("views");

class ForecastGanttModel extends PlanningGanttModel {
    load(searchParams) {
        const groupBy = searchParams.groupBy.slice();
        if (searchParams.context.planning_groupby_project && !groupBy.length) {
            groupBy.unshift("project_id");
        }
        return super.load({ ...searchParams, groupBy });
    }
}

viewRegistry.add("forecast_gantt", {
    ...PlanningGanttView,
    Model: ForecastGanttModel,
});
