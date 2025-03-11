import { patch } from "@web/core/utils/patch";
import * as spreadsheet from "@odoo/o-spreadsheet";
import { useService } from "@web/core/utils/hooks";
import { navigateToOdooMenu } from "./odoo_menu_chartjs_plugin";

patch(spreadsheet.components.FigureComponent.prototype, {
    setup() {
        super.setup();
        this.menuService = useService("menu");
        this.actionService = useService("action");
        this.notificationService = useService("notification");
    },
    async navigateToOdooMenu() {
        const menu = this.env.model.getters.getChartOdooMenu(this.props.figure.id);
        await navigateToOdooMenu(menu, this.actionService, this.notificationService);
    },
    get hasOdooMenu() {
        return this.env.model.getters.getChartOdooMenu(this.props.figure.id) !== undefined;
    },
    async onClick() {
        try {
            const runtime = this.env.model.getters.getChartRuntime(this.props.figure.id);
            if (this.env.isDashboard() && this.hasOdooMenu && runtime && !runtime.chartJsConfig) {
                await this.navigateToOdooMenu();
            }
        } catch {
            return;
        }
    },
});
