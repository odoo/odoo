/** @odoo-module */

import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";

export default class DashboardLinkPlugin extends spreadsheet.UIPlugin {
    constructor(getters, state, dispatch, config, selection) {
        super(...arguments);
        this.env = config.evalContext.env;
        this.selection.observe(this, {
            handleEvent: this.handleEvent.bind(this),
        });
    }

    /**
     * @private
     */
    handleEvent(event) {
        if (!this.getters.isDashboard()) {
            return;
        }
        switch (event.type) {
            case "ZonesSelected": {
                const sheetId = this.getters.getActiveSheetId();
                const { col, row } = event.anchor.cell;
                const cell = this.getters.getCell(sheetId, col, row);
                if (cell !== undefined && cell.isLink()) {
                    cell.action(this.env);
                }
            }
        }
    }
}
