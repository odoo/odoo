/** @odoo-module */

import { coreTypes, CorePlugin } from "@odoo/o-spreadsheet";

/** Plugin that link charts with Odoo actions. It can contain either the Id of the odoo action, or its xml id. */
export default class ChartOdooActionPlugin extends CorePlugin {
    constructor(config) {
        super(config);
        this.odooActionReference = {};
    }

    /**
     * Handle a spreadsheet command
     * @param {Object} cmd Command
     */
    handle(cmd) {
        switch (cmd.type) {
            case "LINK_ODOO_ACTION_TO_CHART":
                this.history.update("odooActionReference", cmd.chartId, cmd.odooActionId);
                break;
            case "DELETE_FIGURE":
                this.history.update("odooActionReference", cmd.id, undefined);
                break;
        }
    }

    /**
     * Get odoo action linked to the chart
     *
     * @param {string} chartId
     * @returns {object | undefined}
     */
    getChartOdooAction(chartId) {
        return this.odooActionReference[chartId];
    }

    import(data) {
        if (data.chartOdooActionsReferences) {
            this.odooActionReference = data.chartOdooActionsReferences;
        }
    }

    export(data) {
        data.chartOdooActionsReferences = this.odooActionReference;
    }
}
ChartOdooActionPlugin.getters = ["getChartOdooAction"];

coreTypes.add("LINK_ODOO_ACTION_TO_CHART");
