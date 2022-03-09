/** @odoo-module **/

import { BurndownChartPivotModel } from "./burndown_chart_pivot_model";
import { PivotView } from "@web/views/pivot/pivot_view";
import { registry } from "@web/core/registry";

const viewRegistry = registry.category("views");

class BurndownChartPivotView extends PivotView {}
BurndownChartPivotView.Model = BurndownChartPivotModel;

viewRegistry.add("burndown_chart_pivot", BurndownChartPivotView);
