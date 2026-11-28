import { registry } from "@web/core/registry";
import { formatMonetary } from "@web/views/fields/formatters";
import {
    JournalDashboardGraphField,
    journalDashboardGraphField,
} from "@web/views/fields/journal_dashboard_graph/journal_dashboard_graph_field";

export class PosDashboardGraphField extends JournalDashboardGraphField {
    getLineChartConfig() {
        const config = super.getLineChartConfig();
        const currencyId = this.props.record.data.currency_id.id;
        const total = this.data[0].values.reduce((sum, pt) => sum + pt.y, 0);
        const format = (value) => formatMonetary(value, { currencyId });
        Object.assign(config.options.plugins.tooltip.callbacks, {
            title: ([item]) => `${item.label}: ${format(item.raw.y)}`,
            label: () => `${this.data[0].key}: ${format(total)}`,
        });
        return config;
    }
}

registry.category("fields").add("pos_dashboard_graph", {
    ...journalDashboardGraphField,
    component: PosDashboardGraphField,
});
