/** @odoo-module */

import { ForecastKanbanController } from './forecast_controllers';
import { ForecastKanbanModel } from './forecast_models';
import { ForecastKanbanRenderer } from './forecast_renderers';
import { ForecastSearchModel } from "./forecast_search_model";
import { graphView } from "@web/views/graph/graph_view";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { listView } from "@web/views/list/list_view";
import { pivotView } from "@web/views/pivot/pivot_view";
import { registry } from "@web/core/registry";
import viewRegistry from 'web.view_registry';

/**
 * Graph view to be used for a Forecast @see ForecastSearchModel
 * requires:
 * - context key `forecast_field` on a date/datetime field
 * - special filter "Forecast" (which must set the `forecast_filter:1` context key)
 */
export const forecastGraphView = {
    ...graphView,
    SearchModel: ForecastSearchModel,
};

registry.category("views").add("forecast_graph", forecastGraphView);

/**
 * Kanban view to be used for a Forecast
 * @see ForecastModelExtension
 * @see FillTemporalService
 * @see ForecastKanbanColumnQuickCreate
 * requires:
 * - context key `forecast_field` on a date/datetime field
 * - special filter "Forecast" (which must set the `forecast_filter:1` context key)
 */
export const forecastKanbanView = {
    ...kanbanView,
    Renderer: ForecastKanbanRenderer,
    Model: ForecastKanbanModel,
    Controller: ForecastKanbanController,
};
/*
    _createSearchModel(params, extraExtensions={}) {
        Object.assign(extraExtensions, { forecast: {} });
        return this._super(params, extraExtensions);
    },

*/
registry.category("views").add("forecast_kanban", forecastKanbanView);

/**
 * List view to be used for a Forecast @see ForecastModelExtension
 * requires:
 * - context key `forecast_field` on a date/datetime field
 * - special filter "Forecast" (which must set the `forecast_filter:1` context key)
 */
export const forecastListView = {
    ...listView,
};
/*
    _createSearchModel(params, extraExtensions = {}) {
        Object.assign(extraExtensions, { forecast: {} });
        return this._super(params, extraExtensions);
    },
*/
registry.category("views").add("forecast_list", forecastListView);

/**
 * Pivot view to be used for a Forecast @see ForecastSearchModel
 * requires:
 * - context key `forecast_field` on a date/datetime field
 * - special filter "Forecast" (which must set the `forecast_filter:1` context key)
 */
export const forecastPivotView = {
    ...pivotView,
    SearchModel: ForecastSearchModel,
};

registry.category("views").add("forecast_pivot", forecastPivotView);
