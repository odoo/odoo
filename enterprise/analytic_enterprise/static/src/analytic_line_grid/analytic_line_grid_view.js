/** @odoo-module */

import { registry } from "@web/core/registry";

import { gridView } from "@web_grid/views/grid_view";

import { AnalyticLineGridModel } from "./analytic_line_grid_model";

export const analyticLineGridView = {
    ...gridView,
    Model: AnalyticLineGridModel,
}

registry.category("views").add("analytic_line_grid", analyticLineGridView)
