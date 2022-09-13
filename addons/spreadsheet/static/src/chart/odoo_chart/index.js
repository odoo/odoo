/** @odoo-module */

import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";

const { chartComponentRegistry } = spreadsheet.registries;
const { ChartJsComponent } = spreadsheet.components;
const { invalidateEvaluationCommands, readonlyAllowedCommands } = spreadsheet;

chartComponentRegistry.add("odoo_bar", ChartJsComponent);
chartComponentRegistry.add("odoo_line", ChartJsComponent);
chartComponentRegistry.add("odoo_pie", ChartJsComponent);

invalidateEvaluationCommands.add("ADD_GRAPH_DOMAIN");
readonlyAllowedCommands.add("ADD_GRAPH_DOMAIN");
