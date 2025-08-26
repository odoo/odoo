import { stores, registries } from "@odoo/o-spreadsheet";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

const { chartSubtypeRegistry } = registries;

patch(stores.ChartDashboardMenuStore.prototype, {
    handle(cmd) {
        switch (cmd.type) {
            case "UPDATE_CHART_GRANULARITY": {
                if (cmd.chartId === this.chartId) {
                    const definition = this.getters.getChartDefinition(this.chartId);
                    this.originalChartDefinition = {
                        ...this.originalChartDefinition,
                        searchParams: definition.searchParams,
                        metaData: definition.metaData,
                    };
                }
                break;
            }
        }
        super.handle(cmd);
    },
    get changeChartTypeMenuItems() {
        const definition = this.getters.getChartDefinition(this.chartId);
        if (["odoo_bar", "odoo_line", "odoo_pie"].includes(definition.type)) {
            return ["odoo_bar", "odoo_line", "odoo_pie"].map((type) => {
                const item = chartSubtypeRegistry.get(type);
                return {
                    id: item.chartType,
                    label: _t("Show as %(chart_type)s chart", {
                        chart_type: item.displayName.toLowerCase(),
                    }),
                    onClick: () => this.updateType(item.chartType),
                    class: item.chartType === definition.type ? "active" : "",
                    preview: item.preview,
                };
            });
        }
        return super.changeChartTypeMenuItems;
    },
    updateType(type) {
        if (!type.startsWith("odoo_")) {
            return super.updateType(type);
        }
        const chartId = this.chartId;
        const currentDefinition = this.getters.getChartDefinition(chartId);
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
        this.model.dispatch("UPDATE_CHART", {
            definition,
            chartId,
            figureId: this.getters.getFigureIdFromChartId(chartId),
            sheetId: this.getters.getActiveSheetId(),
        });
    },
});
