/** @odoo-module */

import GraphView from 'web.GraphView';
import viewRegistry from 'web.view_registry';

/**
 * Graph view to be used for a Forecast @see ForecastModelExtension
 * requires:
 * - context key `forecast_field` on a date/datetime field
 * - special filter "Forecast" (which must set the `forecast_filter:1` context key)
 */
const ForecastGraphView = GraphView.extend({
    /**
     * @private
     * @override
     */
    _createSearchModel(params, extraExtensions = {}) {
        Object.assign(extraExtensions, { Forecast: {} });
        return this._super(params, extraExtensions);
    },
});
viewRegistry.add('forecast_graph', ForecastGraphView);
