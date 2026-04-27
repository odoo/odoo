import { registry } from "@web/core/registry";
import { pivotView } from "@web/views/pivot/pivot_view";
import { TimesheetAnalysisPivotModel } from "./timesheet_analysis_pivot_model";

const viewRegistry = registry.category("views");

export const timesheetAnalysysPivotView = {
    ...pivotView,
    Model: TimesheetAnalysisPivotModel,
};

viewRegistry.add("timesheet_analysis_pivot_view", timesheetAnalysysPivotView);
