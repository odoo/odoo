import { OdooCorePlugin } from "@spreadsheet/plugins";
import { coreTypes, constants } from "@odoo/o-spreadsheet";
const { FIGURE_ID_SPLITTER } = constants;

/** Plugin that link charts with Odoo menus. It can contain either the Id of the odoo menu, or its xml id. */
export class ChartOdooMenuPlugin extends OdooCorePlugin {
    static getters = /** @type {const} */ (["getChartOdooMenu"]);
    constructor(config) {
        super(config);
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
            case "DELETE_CHART":
                this.history.update("odooMenuReference", cmd.chartId, undefined);
                break;
            case "DUPLICATE_SHEET":
                this.updateOnDuplicateSheet(cmd.sheetId, cmd.sheetIdTo);
                break;
        }
    }

    updateOnDuplicateSheet(sheetIdFrom, sheetIdTo) {
        for (const oldChartId of this.getters.getChartIds(sheetIdFrom)) {
            const menu = this.odooMenuReference[oldChartId];
            if (!menu) {
                continue;
            }
            const chartIdBase = oldChartId.split(FIGURE_ID_SPLITTER).pop();
            const newChartId = `${sheetIdTo}${FIGURE_ID_SPLITTER}${chartIdBase}`;
            this.history.update("odooMenuReference", newChartId, menu);
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

coreTypes.add("LINK_ODOO_MENU_TO_CHART");
