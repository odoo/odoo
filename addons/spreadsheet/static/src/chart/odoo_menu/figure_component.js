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
    get chartId() {
        if (this.props.figureUI.tag !== "chart" && this.props.figureUI.tag !== "carousel") {
            return undefined;
        }
        return this.env.model.getters.getChartIdFromFigureId(this.props.figureUI.id);
    },
    async navigateToOdooMenu(newWindow) {
        const menu = this.env.model.getters.getChartOdooMenu(this.chartId);
        await navigateToOdooMenu(menu, this.actionService, this.notificationService, newWindow);
    },
    get hasOdooMenu() {
        return this.chartId && this.env.model.getters.getChartOdooMenu(this.chartId) !== undefined;
    },
    async onClick() {
        try {
            const definition = this.env.model.getters.getChartDefinition(this.chartId);
            if (
                this.env.isDashboard() &&
                this.hasOdooMenu &&
                (definition.type === "scorecard" || definition.type === "gauge")
            ) {
                await this.navigateToOdooMenu();
            }
        } catch {
            // Throws if the figure isn't a chart
        }
    },
});
