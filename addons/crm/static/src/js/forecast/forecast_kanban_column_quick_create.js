/** @odoo-module */

import { useService } from "@web/core/utils/hooks";
import { KanbanColumnQuickCreate } from "@web/views/kanban/kanban_column_quick_create";

const { Component, useState } = owl;

/**
 * Widget to handle events related to the Add button in
 * ForecastKanban views. The view is supposed to automatically add
 * the next column (chronological order), and use the
 * FillTemporalService which will handle the covered fill_temporal period
 * to know which column to add.
 */
export class ForecastColumnQuickCreate extends KanbanColumnQuickCreate {
    setup() {
        super.setup();
        this.fillTemporalService = useService("fillTemporalService");
        let [groupby, granularity] = this.__owl__.parent.props.list.groupBy[0].split(":");
        const forecastField = this.__owl__.parent.props.list.model.rootParams.context.forecast_field;
        if (forecastField && groupby === forecastField) {
            granularity = granularity || "month";
            this.addColumnLabel = _.str.sprintf(this.env._t('Add next %s'), granularity);
        }
    }

    /**
     * @param {MouseEvent} event
     */
    onAddColumnClicked() {
        let [groupby, granularity] = this.__owl__.parent.props.list.groupBy[0].split(":");
        const groupbyType = this.__owl__.parent.props.list.fields[groupby].type;
        const caca = this.fillTemporalService.getFillTemporalPeriod({
            modelName: 'crm.lead',
            field: {
                name: groupby,
                type: groupbyType,
            },
            granularity: granularity,
        }).expand();
        debugger;
        this.mutex.exec(() => this.update(
            { groupBy: [`${this.model.forecast_field}:${this.model.granularity}`] },
            { reload: true }
        ));
        if (this.state.columnTitle.length) {
            this.props.onValidate(this.state.columnTitle);
            this.state.columnTitle = "";
        }
    }
}

ForecastColumnQuickCreate.template = "KanbanView.ForecastColumnQuickCreate";
