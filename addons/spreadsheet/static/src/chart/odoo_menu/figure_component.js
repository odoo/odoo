/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import * as spreadsheet from "@odoo/o-spreadsheet";
import { useService } from "@web/core/utils/hooks";

patch(spreadsheet.components.FigureComponent.prototype, "spreadsheet.FigureComponent", {
    setup() {
        this._super();
        this.actionService = useService("action");
    },
    async executeOdooAction() {
        const action = this.env.model.getters.getChartOdooAction(this.props.figure.id);
        if (!action) {
            throw new Error(`Cannot find any action associated with the chart`);
        }
        await this.actionService.doAction(action);
    },
    get hasOdooAction() {
        return this.env.model.getters.getChartOdooAction(this.props.figure.id) !== undefined;
    },
    async onClick() {
        if (this.env.isDashboard() && this.hasOdooAction) {
            this.executeOdooAction();
        }
    },
});
