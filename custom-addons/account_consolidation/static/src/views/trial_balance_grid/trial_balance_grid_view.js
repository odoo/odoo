/** @odoo-module */

import { registry } from "@web/core/registry";
import { gridView } from "@web_grid/views/grid_view";

import { ConsolidationGridController } from "./trial_balance_grid_controller";
import { ConsolidationGridModel } from "./trial_balance_grid_model";

export const consolidationGridView = {
    ...gridView,
    buttonTemplate: 'account_consolidation.GridButtons',
    Controller: ConsolidationGridController,
    Model: ConsolidationGridModel,
};

registry.category("views").add("consolidation_grid", consolidationGridView);
