/** @odoo-module */
import Widget from 'web.Widget';
import { _t } from 'web.core';

/**
 * Widget to handle events related to the Add button in
 * ForecastKanban views. The view is supposed to automatically add
 * the next column (chronological order), and use the
 * FillTemporalService which will handle the covered fill_temporal period
 * to know which column to add.
 */
const ForecastColumnQuickCreate = Widget.extend({
    template: 'KanbanView.ForecastColumnQuickCreate',
    events: {
        'click .o_quick_create_folded': '_onAddColumnClicked',
    },

    /**
     * @override
     * @param {Object} options
     * @param {string} [options.addColumnLabel] displayed label
     *        (should be the granularity of a date/datetime groupBy)
     */
    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.addColumnLabel = _.str.sprintf(_t('Add next %s'), options.addColumnLabel);
    },

    /**
     * Notify the environment to add a column
     *
     * @private
     */
    _addColumn: function () {
        this.trigger_up('forecast_kanban_add_column', {});
    },

    /**
     * @private
     * @param {MouseEvent} event
     */
    _onAddColumnClicked: function (event) {
        event.stopPropagation();
        this._addColumn();
    },
});

export default ForecastColumnQuickCreate;
