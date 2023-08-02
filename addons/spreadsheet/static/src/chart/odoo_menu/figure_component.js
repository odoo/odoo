/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import * as spreadsheet from "@odoo/o-spreadsheet";
import { useService } from "@web/core/utils/hooks";

patch(spreadsheet.components.FigureComponent.prototype, {
    setup() {
        super.setup();
        this.menuService = useService("menu");
        this.actionService = useService("action");
    },
    async navigateToOdooMenu() {
        const menu = this.env.model.getters.getChartOdooMenu(this.props.figure.id);
        if (!menu) {
            throw new Error(`Cannot find any menu associated with the chart`);
        }
        await this.actionService.doAction(menu.actionID);
    },
    get hasOdooMenu() {
        return this.env.model.getters.getChartOdooMenu(this.props.figure.id) !== undefined;
    },
    async onClick() {
        if (this.env.isDashboard() && this.hasOdooMenu) {
            this.navigateToOdooMenu();
        }
    },
});
