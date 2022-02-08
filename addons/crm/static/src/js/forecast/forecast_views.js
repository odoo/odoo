/** @odoo-module */
import { ForecastKanbanController } from './forecast_controllers';
import { ForecastKanbanModel } from './forecast_models';
import { ForecastKanbanRenderer } from './forecast_renderers';
import { ForecastSearchModel } from "./forecast_search_model";
import { GraphView } from "@web/views/graph/graph_view";
import KanbanView from 'web.KanbanView';
import ListView from 'web.ListView';
import { PivotView } from "@web/views/pivot/pivot_view";
import { registry } from "@web/core/registry";
import viewRegistry from 'web.view_registry';

/**
 * Graph view to be used for a Forecast @see ForecastSearchModel
 * requires:
 * - context key `forecast_field` on a date/datetime field
 * - special filter "Forecast" (which must set the `forecast_filter:1` context key)
 */
class ForecastGraphView extends GraphView {}
ForecastGraphView.SearchModel = ForecastSearchModel;

registry.category("views").add("forecast_graph", ForecastGraphView);

/**
 * Kanban view to be used for a Forecast
 * @see ForecastModelExtension
 * @see FillTemporalService
 * @see ForecastKanbanColumnQuickCreate
 * requires:
 * - context key `forecast_field` on a date/datetime field
 * - special filter "Forecast" (which must set the `forecast_filter:1` context key)
 */
const ForecastKanbanView = KanbanView.extend({
    config: _.extend({}, KanbanView.prototype.config, {
        Renderer: ForecastKanbanRenderer,
        Model: ForecastKanbanModel,
        Controller: ForecastKanbanController,
    }),
    /**
     * @private
     * @override
     */
    _createSearchModel(params, extraExtensions={}) {
        Object.assign(extraExtensions, { forecast: {} });
        return this._super(params, extraExtensions);
    },
});
viewRegistry.add('forecast_kanban', ForecastKanbanView);

/**
 * List view to be used for a Forecast @see ForecastModelExtension
 * requires:
 * - context key `forecast_field` on a date/datetime field
 * - special filter "Forecast" (which must set the `forecast_filter:1` context key)
 */
const ForecastListView = ListView.extend({
    /**
     * @private
     * @override
     */
    _createSearchModel(params, extraExtensions = {}) {
        Object.assign(extraExtensions, { forecast: {} });
        return this._super(params, extraExtensions);
    },
});
viewRegistry.add('forecast_list', ForecastListView);

/**
 * Pivot view to be used for a Forecast @see ForecastSearchModel
 * requires:
 * - context key `forecast_field` on a date/datetime field
 * - special filter "Forecast" (which must set the `forecast_filter:1` context key)
 */
class ForecastPivotView extends PivotView {}
ForecastPivotView.SearchModel = ForecastSearchModel;

registry.category("views").add("forecast_pivot", ForecastPivotView);

export {
    ForecastGraphView,
    ForecastKanbanView,
    ForecastListView,
    ForecastPivotView,
};
