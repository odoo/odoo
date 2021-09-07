/** @odoo-module **/

import { GraphView } from "@web/views/graph/graph_view";
import { hrTimesheetGraphModel } from "./timesheet_graph_model";
import { registry } from "@web/core/registry";

const viewRegistry = registry.category("views");

export class hrTimesheetGraphView extends GraphView {}
hrTimesheetGraphView.Model = hrTimesheetGraphModel;

viewRegistry.add("hr_timesheet_graphview", hrTimesheetGraphView);
