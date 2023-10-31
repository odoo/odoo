/** @odoo-module **/

import { BurndownChartRenderer } from "./burndown_chart_renderer";
import { GraphView } from "@web/views/graph/graph_view";
import { registry } from "@web/core/registry";

const viewRegistry = registry.category("views");

class BurndownChartView extends GraphView {}
BurndownChartView.components = { ...GraphView.components, Renderer: BurndownChartRenderer };
BurndownChartView.buttonTemplate = "project.BurndownChartView.Buttons";

viewRegistry.add("burndown_chart", BurndownChartView);
