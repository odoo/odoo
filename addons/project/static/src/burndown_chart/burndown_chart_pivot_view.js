/** @odoo-module **/

import { BurndownChartPivotModel } from "./burndown_chart_pivot_model";
import { pivotView } from "@web/views/pivot/pivot_view";
import { registry } from "@web/core/registry";

const viewRegistry = registry.category("views");

const burndownChartPivotView = {...pivotView, Model: BurndownChartPivotModel};
viewRegistry.add("burndown_chart_pivot", burndownChartPivotView);
