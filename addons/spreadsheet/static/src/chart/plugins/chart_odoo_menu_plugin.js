/** @odoo-module */

import { coreTypes, CorePlugin } from "@odoo/o-spreadsheet";

/** Plugin that link charts with Odoo menus. It can contain either the Id of the odoo menu, or its xml id. */
export default class ChartOdooMenuPlugin extends CorePlugin {
    constructor(config) {
        super(config);
    }

    /**
     * Handle a spreadsheet command
     * @param {Object} cmd Command
     */
    handle(cmd) {
        switch (cmd.type) {
            case "LINK_ODOO_MENU_TO_CHART":
                {
                    const definition = this.getters.getChartDefinition(cmd.chartId);
                    this.dispatch("UPDATE_CHART", {
                        definition: {
                            ...definition,
                            extraData: { ...definition.extraData, odooMenuId: cmd.odooMenuId },
                        },
                        id: cmd.chartId,
                        sheetId: this.getters.getFigureSheetId(cmd.chartId),
                    });
                }
                break;
        }
    }

    /**
     * Get odoo menu linked to the chart
     *
     * @param {string} chartId
     * @returns {object | undefined}
     */
    getChartOdooMenu(chartId) {
        try {
            const definition = this.getters.getChartDefinition(chartId);
            if (definition.extraData && definition.extraData.odooMenuId) {
                return this.getters.getIrMenu(definition.extraData.odooMenuId);
            }
        } catch {
            // Ignore error if the chart doesn't exist anymore
            return undefined;
        }
    }
}

ChartOdooMenuPlugin.getters = ["getChartOdooMenu"];

coreTypes.add("LINK_ODOO_MENU_TO_CHART");
