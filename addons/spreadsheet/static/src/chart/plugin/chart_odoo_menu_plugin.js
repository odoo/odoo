/** @odoo-module */

import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
const { corePluginRegistry } = spreadsheet.registries;
const { coreTypes } = spreadsheet;

/** Plugin that link charts with Odoo menus. It can contain either the Id of the odoo menu, or its xml id. */
export default class ChartOdooMenuPlugin extends spreadsheet.CorePlugin {
    constructor() {
        super(...arguments);
        this.odooMenuReference = {};
    }

    /**
     * Handle a spreadsheet command
     * @param {Object} cmd Command
     */
    handle(cmd) {
        switch (cmd.type) {
            case "LINK_ODOO_MENU_TO_CHART":
                this.history.update("odooMenuReference", cmd.chartId, cmd.odooMenuId);
                break;
            case "DELETE_FIGURE":
                this.history.update("odooMenuReference", cmd.id, undefined);
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
        const menuId = this.odooMenuReference[chartId];
        return menuId ? this.getters.getIrMenu(menuId) : undefined;
    }

    import(data) {
        if (data.chartOdooMenusReferences) {
            this.odooMenuReference = data.chartOdooMenusReferences;
        }
    }

    export(data) {
        data.chartOdooMenusReferences = this.odooMenuReference;
    }
}
ChartOdooMenuPlugin.modes = ["normal", "headless"];
ChartOdooMenuPlugin.getters = ["getChartOdooMenu"];

corePluginRegistry.add("chartOdooMenuPlugin", ChartOdooMenuPlugin);
coreTypes.add("LINK_ODOO_MENU_TO_CHART");
