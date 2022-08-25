/** @odoo-module */
import ForecastColumnQuickCreate from './forecast_kanban_column_quick_create';
import KanbanRenderer from 'web.KanbanRenderer';

const ForecastKanbanRenderer = KanbanRenderer.extend({
    /**
     * Adds the widget ForecastColumnQuickCreate if there is a forecast_field and the current
     * groupby targets it. It will be used to automatically add the next group for a date/datetime
     * field
     *
     * @private
     * @override
     * @param {DocumentFragment} fragment
     */
    _renderGrouped(fragment) {
        this._super(...arguments);
        let [groupby, granularity] = this.state.groupedBy[0].split(":");
        const forecast_field = this.state.context.forecast_field;
        if (forecast_field && groupby === forecast_field) {
            granularity = granularity || "month";
            this.forecastColumnQuickCreate = new ForecastColumnQuickCreate(this, {
                addColumnLabel: granularity,
            });
            this.defs.push(this.forecastColumnQuickCreate.appendTo(fragment));
        }
    },
});

export {
    ForecastKanbanRenderer,
};
