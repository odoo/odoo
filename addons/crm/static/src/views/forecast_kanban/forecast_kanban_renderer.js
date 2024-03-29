/** @odoo-module **/

import { CrmKanbanRenderer } from "@crm/views/crm_kanban/crm_kanban_renderer";
import { useService } from "@web/core/utils/hooks";
import { ForecastKanbanColumnQuickCreate } from "@crm/views/forecast_kanban/forecast_kanban_column_quick_create";

export class ForecastKanbanRenderer extends CrmKanbanRenderer {
    setup() {
        super.setup(...arguments);
        this.fillTemporalService = useService("fillTemporalService");
    }
    /**
     * @override
     *
     * Allow creating groups when grouping by forecast_field.
     */
    canCreateGroup() {
        return super.canCreateGroup(...arguments) || this.isGroupedByForecastField();
    }

    isGroupedByForecastField() {
        return (
            this.props.list.context.forecast_field &&
            this.props.list.groupByField.name === this.props.list.context.forecast_field
        );
    }

    isMovableField(field) {
        return super.isMovableField(...arguments) || field.name === "date_deadline";
    }

    async addForecastColumn() {
        const { name, type, granularity } = this.props.list.groupByField;
        this.fillTemporalService
            .getFillTemporalPeriod({
                modelName: this.props.list.resModel,
                field: {
                    name,
                    type,
                },
                granularity: granularity || "month",
            })
            .expand();
        await this.props.list.load();
        await this.props.progressBarState?._updateProgressBar();
    }
}

ForecastKanbanRenderer.template = "crm.ForecastKanbanRenderer";
ForecastKanbanRenderer.components = {
    ...CrmKanbanRenderer.components,
    ForecastKanbanColumnQuickCreate,
};
