import { registry } from "@web/core/registry";
import { graphView } from "@web/views/graph/graph_view";
import { hrTimesheetGraphModel } from "./timesheet_graph_model";

const viewRegistry = registry.category("views");

export const hrTimesheetGraphView = {
  ...graphView,
  Model: hrTimesheetGraphModel,
};

viewRegistry.add("hr_timesheet_graphview", hrTimesheetGraphView);
