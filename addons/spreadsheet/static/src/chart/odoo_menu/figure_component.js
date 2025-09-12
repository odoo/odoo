import { patch } from "@web/core/utils/patch";
import * as spreadsheet from "@odoo/o-spreadsheet";
import { useService } from "@web/core/utils/hooks";
import { navigateToOdooMenu } from "../odoo_chart/odoo_chart_helpers";

patch(spreadsheet.components.FigureComponent.prototype, {
    setup() {
        super.setup();
        this.menuService = useService("menu");
        this.actionService = useService("action");
        this.notificationService = useService("notification");
    },
    async navigateToOdooMenu(newWindow) {
        const menu = this.env.model.getters.getChartOdooMenu(this.props.figureUI.id);
        await navigateToOdooMenu(menu, this.actionService, this.notificationService, newWindow);
    },
    get hasOdooMenu() {
        return this.env.model.getters.getChartOdooMenu(this.props.figureUI.id) !== undefined;
    },
    async onClick() {
        const definition = this.env.model.getters.getChartDefinition(this.props.figureUI.id);
        if (this.hasOdooMenu && (definition.type === "scorecard" || definition.type === "gauge")) {
            await this.navigateToOdooMenu();
        }
    },
});
