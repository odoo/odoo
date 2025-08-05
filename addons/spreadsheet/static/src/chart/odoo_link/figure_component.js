import { patch } from "@web/core/utils/patch";
import * as spreadsheet from "@odoo/o-spreadsheet";
import { useService } from "@web/core/utils/hooks";
import { navigateToOdoolinkFromChart } from "../odoo_chart/odoo_chart_helpers";

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
    async navigateToOdooLink(newWindow) {
        await navigateToOdoolinkFromChart(this.env, this.chartId, newWindow);
    },
    get hasOdooLink() {
        return this.env.model.getters.getChartOdooLink(this.chartId) !== undefined;
    },
    async onClick() {
        try {
            const definition = this.env.model.getters.getChartDefinition(this.chartId);
            if (
                this.env.isDashboard() &&
                this.hasOdooLink &&
                (definition.type === "scorecard" || definition.type === "gauge")
            ) {
                await this.navigateToOdooLink();
            }
        } catch {
            // Throws if the figure isn't a chart
        }
    },
});
