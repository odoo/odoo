import { components, registries } from "@odoo/o-spreadsheet";
import { patch } from "@web/core/utils/patch";

const { chartSubtypeRegistry } = registries;

patch(components.ChartDashboardMenu.prototype, {
    get changeChartTypeMenuItems() {
        const definition = this.env.model.getters.getChartDefinition(this.props.figureUI.id);
        if (["odoo_bar", "odoo_line", "odoo_pie"].includes(definition.type)) {
            return ["odoo_bar", "odoo_line", "odoo_pie"].map((type) => {
                const item = chartSubtypeRegistry.get(type);
                return {
                    id: item.chartType,
                    label: item.displayName,
                    onClick: () => this.onTypeChange(item.chartType),
                    isSelected: item.chartType === this.selectedChartType,
                    iconClass: this.getIconClasses(item.chartType),
                };
            });
        }
        return super.changeChartTypeMenuItems;
    },
    onTypeChange(type) {
        if (!type.startsWith("odoo_")) {
            return super.onTypeChange(type);
        }
        const figureId = this.props.figureUI.id;
        const currentDefinition = this.env.model.getters.getChartDefinition(figureId);
        if (currentDefinition.type === type) {
            return;
        }

        const definition =
            this.originalChartDefinition.type === type
                ? this.originalChartDefinition
                : {
                      ...this.originalChartDefinition,
                      ...chartSubtypeRegistry.get(type).subtypeDefinition,
                      type,
                  };

        this.env.model.dispatch("UPDATE_CHART", {
            definition,
            figureId,
            sheetId: this.env.model.getters.getActiveSheetId(),
        });
    },
});
