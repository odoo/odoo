/** @odoo-module **/

import { ProjectGraphView } from "@project/js/project_graph_view";
import { hrTimesheetGraphModel } from "./timesheet_graph_model";
import { registry } from "@web/core/registry";

const viewRegistry = registry.category("views");

export class hrTimesheetGraphView extends ProjectGraphView {}
hrTimesheetGraphView.Model = hrTimesheetGraphModel;

viewRegistry.add("hr_timesheet_graphview", hrTimesheetGraphView);
