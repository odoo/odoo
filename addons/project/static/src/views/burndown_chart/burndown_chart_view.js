/** @odoo-module **/

import { BurndownChartModel } from "./burndown_chart_model";
import { graphView } from "@web/views/graph/graph_view";
import { registry } from "@web/core/registry";
import { BurndownChartSearchModel } from "./burndown_chart_search_model";

const viewRegistry = registry.category("views");

const burndownChartGraphView = {
  ...graphView,
  buttonTemplate: "project.BurndownChartView.Buttons",
  hideCustomGroupBy: true,
  Model: BurndownChartModel,
  searchMenuTypes: graphView.searchMenuTypes.filter(menuType => menuType !== "comparison"),
  SearchModel: BurndownChartSearchModel,
};

viewRegistry.add("burndown_chart", burndownChartGraphView);
