/** @odoo-module **/

import { sprintf } from "@web/core/utils/strings";
import { useService } from "@web/core/utils/hooks";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { ForecastKanbanColumnQuickCreate } from "@crm/views/forecast_kanban/forecast_kanban_column_quick_create";
import { INTERVAL_OPTIONS } from "@web/search/utils/dates";

export class ForecastKanbanRenderer extends KanbanRenderer {
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
        await this.props.list.model.root.load();
        this.props.list.model.notify();
    }

    getForecastQuickCreateTitle() {
        const { granularity } = this.props.list.groupByField;
        return sprintf(this.env._t("Add next %s"), INTERVAL_OPTIONS[granularity || "month"].description.toLocaleLowerCase());
    }
}

ForecastKanbanRenderer.template = "crm.ForecastKanbanRenderer";
ForecastKanbanRenderer.components = {
    ...KanbanRenderer.components,
    ForecastKanbanColumnQuickCreate,
};
