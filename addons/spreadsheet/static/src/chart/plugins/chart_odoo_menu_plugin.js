/** @odoo-module */

import { coreTypes, CorePlugin } from "@odoo/o-spreadsheet";

/** Plugin that link charts with Odoo menus or actions. It can contain either the Id of the odoo menu/action, or its xml id. */
export default class ChartOdooMenuPlugin extends CorePlugin {
    constructor(config) {
        super(config);
        this.odooMenuReference = {};
        this.odooActionReference = {}
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
        const actionID = this.odooActionReference[chartId];
        return menuId ? this.getters.getIrMenu(menuId) : actionID ? { actionID } : undefined;
    }

    import(data) {
        if (data.chartOdooMenusReferences) {
            this.odooMenuReference = data.chartOdooMenusReferences;
        }
        if (data.chartOdooActionsReferences) {
            this.odooActionReference = data.chartOdooActionsReferences;
        }
    }

    export(data) {
        data.chartOdooMenusReferences = this.odooMenuReference;
        data.chartOdooActionsReferences = this.odooActionReference;
    }
}
ChartOdooMenuPlugin.getters = ["getChartOdooMenu"];

coreTypes.add("LINK_ODOO_MENU_TO_CHART");
