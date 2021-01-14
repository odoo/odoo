/** @odoo-module alias=crm.CrmForecastKanban **/
import KanbanRenderer from 'web.KanbanRenderer';
import KanbanModel from 'web.KanbanModel';
import KanbanController from 'web.KanbanController';
import KanbanView from 'web.KanbanView';
import viewRegistry from 'web.view_registry';
import ColumnQuickAdd from 'crm.KanbanColumnQuickAdd';
import pyUtils from 'web.py_utils';
import Class from 'web.Class';

var CrmForecastKanbanRenderer = KanbanRenderer.extend({
    /**
     * @override
     * TODO ABD: better fallback if this kanban is not for a forecast
     */
    _renderGrouped: function (fragment) {
        this._super(...arguments);
        var groupby, granularity;
        [groupby, granularity] = this.state.groupedBy[0].split(":");
        var forecast_field = this.state.context.forecast_field;
        if (typeof forecast_field !== 'undefined' && groupby === forecast_field) {
            if (typeof granularity === 'undefined') {
                granularity = "month";
            }
            this.quickAdd = new ColumnQuickAdd(this, {
                target_field: forecast_field,
                title: `Add next ${granularity}`,
            });
            this.defs.push(this.quickAdd.appendTo(fragment));
        }
    },
});

var ForecastPeriod = Class.extend({
    granularity_table: {
        day: {
            startOf: x => x.startOf('day'),
            cycle: 7,
            cycle_pos: x => x.weekday(),
        },
        week: {
            startOf: x => x.startOf('week'),
            cycle: 1,
            cycle_pos: x => 1,
        },
        month: {
            startOf: x => x.startOf('month'),
            cycle: 12,
            cycle_pos: x => x.month() + 1,
        },
        quarter: {
            startOf: x => x.startOf('quarter'),
            cycle: 4,
            cycle_pos: x => x.quarter(),
        },
        year: {
            startOf: x => x.startOf('year'),
        },
    },
    _get: function(setting) {
        return this.granularity_table[this.granularity][setting];
    },
    _computeStart: function() {
        this.start = this._get("startOf")(moment(pyUtils.context().today));
    },
    /**
     * Compute the moment for the end of the forecast period.
     * The forecast period is the number of [granularity] from [start] to the end of the [cycle] reached after
     * adding [min_period] 
     * i.e. we are in october 2020 :
     *      [start] = 2020-10-1
     *      [granularity] = 'month',
     *      [cycle] = 12
     *      [min_period] = 4,
     *      => forecast_period = 15 months (until end of december 2021)
     */
    _computeEnd: function() {
        var cycle = this._get("cycle");
        if (typeof cycle === 'undefined') {
            this.end = false;
            return;
        }
        var cycle_pos = this._get("cycle_pos")(this.start);
        var min_period = this.min_period;
        var forecast_period = (2 * cycle - (min_period - 1) % cycle - cycle_pos) % cycle + min_period;
        this.end = moment(this.start).add(forecast_period, `${this.granularity}s`);
    },
    init: function (field_name, granularity, min_period) {
        this.field_name = field_name;
        this.granularity = granularity || "month";
        this.min_period = min_period;

        this._computeStart();
        this._computeEnd();
    },
    applyForecastDomain: function(domain) {
        var output = ['&', ...domain, '|', [this.field_name, '=', false]];
        if (this.end) {
            output.push('&', [this.field_name, '<', this.end.format("YYYY-MM-DD")]);
        }
        output.push([this.field_name, '>=', this.start.format("YYYY-MM-DD")]);
        return output;
    },
    applyForecastContext: function(context, greedy=true) {
        var output = {
            ...context,
            fill_temporal_from: this.start.format("YYYY-MM-DD"),
            fill_temporal_min: this.min_period
        };
        if (greedy) {
            output.fill_temporal_to = moment(this.end).subtract(1, 'day').format("YYYY-MM-DD");
        }
        return output;
    },
    expand: function(nb=1) {
        this.end.add(nb, `${this.granularity}s`);
    },
});
    
var CrmForecastKanbanModel = KanbanModel.extend({
    /**
     * @override
     */
    __load: async function (params) {
        this.forecast_domain = params.domain;
        this.forecast_field = params.context.forecast_field;
        this.min_forecast_period = params.context.fill_temporal_min || 4;

        this.forecast_periods = {
            day: new ForecastPeriod(this.forecast_field, "day", this.min_forecast_period),
            week: new ForecastPeriod(this.forecast_field, "week", this.min_forecast_period),
            month: new ForecastPeriod(this.forecast_field, "month", this.min_forecast_period),
            quarter: new ForecastPeriod(this.forecast_field, "quarter", this.min_forecast_period),
            year: new ForecastPeriod(this.forecast_field, "year", this.min_forecast_period),
        };
        this.granularity = "month";
        var forecast = this.forecast_periods[this.granularity];
        params.domain = forecast.applyForecastDomain(params.domain);
        params.context = forecast.applyForecastContext(params.context, false);
        var handle = await this._super(...arguments);
        var columns_data = this.get(handle, {raw: true}).data; // .data[x].value (can be false or a display string)
        var current_forecast_period = columns_data.filter(group => group.value).length;
        forecast.end = moment(forecast.start).add(current_forecast_period, "months");
        return handle;
    },
    /**
     * @override
     */
    __reload: async function (id, options) {
        var forecast = this.forecast_periods[this.granularity];
        var groupby;
        if ("groupBy" in options) {
            var granularity;
            [groupby, granularity] = options.groupBy[0].split(':');
            if (typeof granularity === 'undefined') {
                granularity = "month";
            }
            if (groupby === this.forecast_field && granularity != this.granularity) {
                this.granularity = granularity;
                forecast = this.forecast_periods[granularity];
            }
        }
        options.domain = forecast.applyForecastDomain(this.forecast_domain);
        options.context = forecast.applyForecastContext(this.loadParams.context, forecast.end);
        var reload = await this._super(...arguments);
        if ("groupBy" in options) {
            var columns_data = this.get(id, {raw: true}).data; // .data[x].value (can be false or a display string)
            var current_forecast_period = columns_data.filter(group => group.value).length;
            forecast.end = moment(forecast.start).add(current_forecast_period, `${this.granularity}s`);
        }
        return reload;
    },
});

var CrmForecastKanbanController = KanbanController.extend({
    custom_events: _.extend({}, KanbanController.prototype.custom_events, {
        forecast_kanban_add_column: '_onAddColumnForecast',
    }),
    _onAddColumnForecast: function (ev) {
        // ev.data.value -> "date_deadline" (to be deleted, usage example)
        this.model.forecast_periods[this.model.granularity].expand();
        const self = this;
        this.mutex.exec(function () {
            return self.update({}, {reload: true});
        }).then(function () {
            return self.renderer.trigger_up("quick_create_column_created");
        });
    },
});

var CrmForecastKanbanView = KanbanView.extend({
    config: _.extend({}, KanbanView.prototype.config, {
        Renderer: CrmForecastKanbanRenderer,
        Model: CrmForecastKanbanModel,
        Controller: CrmForecastKanbanController,
    }),
});

viewRegistry.add('crm_forecast_kanban', CrmForecastKanbanView);

export default {
    CrmForecastKanbanRenderer: CrmForecastKanbanRenderer,
    CrmForecastKanbanModel: CrmForecastKanbanModel,
    CrmForecastKanbanController: CrmForecastKanbanController,
    CrmForecastKanbanView: CrmForecastKanbanView,
};
