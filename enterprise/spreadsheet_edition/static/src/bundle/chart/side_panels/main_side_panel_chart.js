/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import * as spreadsheet from "@odoo/o-spreadsheet";
import { onWillUpdateProps } from "@odoo/owl";

const { chartSubtypeRegistry } = spreadsheet.registries;
const { ChartTypePicker } = spreadsheet.components;

/**
 * This patch is necessary to ensure that the chart type cannot be changed
 * between odoo charts and spreadsheet charts.
 */

patch(ChartTypePicker.prototype, {
    setup() {
        super.setup();
        this.updateChartTypeByCategories(this.props);
        onWillUpdateProps((nexProps) => this.updateChartTypeByCategories(nexProps));
    },

    /**
     * @param {boolean} isOdoo
     */
    getChartTypes(isOdoo) {
        const result = {};
        for (const key of chartSubtypeRegistry.getKeys()) {
            if ((isOdoo && key.startsWith("odoo_")) || (!isOdoo && !key.startsWith("odoo_"))) {
                result[key] = chartSubtypeRegistry.get(key).name;
            }
        }
        return result;
    },

    onTypeChange(type) {
        if (this.getChartDefinition(this.props.figureId).type.startsWith("odoo_")) {
            const newChartInfo = chartSubtypeRegistry.get(type);
            const definition = {
                verticalAxisPosition: "left",
                ...this.env.model.getters.getChartDefinition(this.props.figureId),
                ...newChartInfo.subtypeDefinition,
                type: newChartInfo.chartType,
            };
            this.env.model.dispatch("UPDATE_CHART", {
                definition,
                id: this.props.figureId,
                sheetId: this.env.model.getters.getActiveSheetId(),
            });
            this.closePopover();
        } else {
            super.onTypeChange(type);
        }
    },
    updateChartTypeByCategories(props) {
        const definition = this.env.model.getters.getChartDefinition(props.figureId);
        const isOdoo = definition.type.startsWith("odoo_");
        const registryItems = chartSubtypeRegistry.getAll().filter((item) => {
            return isOdoo
                ? item.chartType.startsWith("odoo_")
                : !item.chartType.startsWith("odoo_");
        });

        this.chartTypeByCategories = {};
        for (const chartInfo of registryItems) {
            if (this.chartTypeByCategories[chartInfo.category]) {
                this.chartTypeByCategories[chartInfo.category].push(chartInfo);
            } else {
                this.chartTypeByCategories[chartInfo.category] = [chartInfo];
            }
        }
    },
});
