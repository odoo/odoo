/** @odoo-module */
import KanbanController from 'web.KanbanController';

const ForecastKanbanController = KanbanController.extend({
    custom_events: _.extend({}, KanbanController.prototype.custom_events, {
        forecast_kanban_add_column: '_onAddColumnForecast',
    }),

    /**
     * Expand the fill_temporal period after the ForecastColumnQuickCreate has been used, then
     * reload the view to refetch updated data
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onAddColumnForecast(ev) {
        ev.stopPropagation();
        this.call('fillTemporalService', 'getFillTemporalPeriod', {
            modelName: this.model.loadParams.modelName,
            field: {
                name: this.model.forecast_field,
                type: this.model.loadParams.fields[this.model.forecast_field].type,
            },
            granularity: this.model.granularity,
        }).expand();
        this.mutex.exec(() => this.update(
            { groupBy: [`${this.model.forecast_field}:${this.model.granularity}`] },
            { reload: true }
        ));
    },
});

export {
    ForecastKanbanController,
};
