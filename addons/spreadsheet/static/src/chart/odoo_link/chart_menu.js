import { patch } from "@web/core/utils/patch";
import * as spreadsheet from "@odoo/o-spreadsheet";
import { navigateToOdoolinkFromChart } from "../odoo_chart/odoo_chart_helpers";
import { _t } from "@web/core/l10n/translation";

patch(spreadsheet.components.ChartMenu.prototype, {
    getMenuItems() {
        const items = super.getMenuItems();
        if (this.hasOdooLink && !this.env.model.getters.isDashboard()) {
            items.push({
                id: "chartOdooLink",
                label: _t("Chart Odoo Link"),
                icon: "o-spreadsheet-Icon.EXTERNAL",
                onClick: (ev) => this.navigateToOdooLink(false),
            });
        }
        return items;
    },
    async navigateToOdooLink(newWindow) {
        await navigateToOdoolinkFromChart(this.env, this.props.chartId, newWindow);
    },
    get hasOdooLink() {
        return this.env.model.getters.getChartOdooLink(this.props.chartId) !== undefined;
    },
});
