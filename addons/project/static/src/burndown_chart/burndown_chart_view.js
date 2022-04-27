/** @odoo-module **/

import { BurndownChartModel } from "./burndown_chart_model";
import { BurndownChartRenderer } from "./burndown_chart_renderer";
import { graphView } from "@web/views/graph/graph_view";
import { registry } from "@web/core/registry";

const viewRegistry = registry.category("views");

const burndownChartGraphView = {
  ...graphView,
  Renderer: BurndownChartRenderer,
  buttonTemplate: "project.BurndownChartView.Buttons",
  Model: BurndownChartModel,
};

viewRegistry.add("burndown_chart", burndownChartGraphView);
