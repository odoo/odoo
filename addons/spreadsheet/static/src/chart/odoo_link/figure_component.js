import { patch } from "@web/core/utils/patch";
import * as spreadsheet from "@odoo/o-spreadsheet";
import { useService } from "@web/core/utils/hooks";
import { navigateToOdoolinkFromChart } from "../odoo_chart/odoo_chart_helpers";

patch(spreadsheet.components.FigureComponent.prototype, {
    setup() {
        super.setup();
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
});

patch(spreadsheet.components.ScorecardChart.prototype, {
    setup() {
        super.setup();
        this.actionService = useService("action");
        this.notificationService = useService("notification");
    },
    async navigateToOdooLink(newWindow) {
        await navigateToOdoolinkFromChart(this.env, this.props.chartId, newWindow);
    },
    get hasOdooLink() {
        return this.env.model.getters.getChartOdooLink(this.props.chartId) !== undefined;
    },
    async onClick() {
        if (this.env.isDashboard() && this.hasOdooLink) {
            await this.navigateToOdooLink();
        }
    },
});

patch(spreadsheet.components.GaugeChartComponent.prototype, {
    setup() {
        super.setup();
        this.actionService = useService("action");
        this.notificationService = useService("notification");
    },
    async navigateToOdooLink(newWindow) {
        await navigateToOdoolinkFromChart(this.env, this.props.chartId, newWindow);
    },
    get hasOdooLink() {
        return this.env.model.getters.getChartOdooLink(this.props.chartId) !== undefined;
    },
    async onClick() {
        if (this.env.isDashboard() && this.hasOdooLink) {
            await this.navigateToOdooLink();
        }
    },
});
