import { cookie } from "@web/core/browser/cookie";
import { getCustomColor } from "@web/core/colors/colors";
import { registry } from "@web/core/registry";
import {
    JournalDashboardGraphField,
    journalDashboardGraphField,
} from "@web/views/fields/journal_dashboard_graph/journal_dashboard_graph_field";

const colorScheme = cookie.get("color_scheme");
const GRAPH_GRID_COLOR = getCustomColor(colorScheme, "#d8dadd", "#3C3E4B");
const GRAPH_LABEL_COLOR = getCustomColor(colorScheme, "#6c757d", "#ADB5BD");

export class AccountJournalDashboardGraphField extends JournalDashboardGraphField {
    getBarChartConfig() {
        if (this.data[0].type !== "monthly_total") {
            return super.getBarChartConfig();
        }

        return this.getMonthlyTotalChartConfig();
    }

    getMonthlyTotalChartConfig() {
        const totalColor = "#875A7B";

        return {
            type: "bar",
            data: {
                labels: this.data[0].labels,
                datasets: [
                    {
                        backgroundColor: totalColor,
                        data: this.data[0].values,
                        label: this.data[0].key,
                        borderWidth: 0,
                    },
                ],
            },
            options: {
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        position: "nearest",
                        caretSize: 0,
                    },
                },
                scales: {
                    y: {
                        display: false,
                    },
                    x: {
                        grid: {
                            display: false,
                        },
                        ticks: {
                            color: GRAPH_LABEL_COLOR,
                        },
                        border: {
                            color: GRAPH_GRID_COLOR,
                        },
                    },
                },
                maintainAspectRatio: false,
                interaction: {
                    intersect: true,
                    mode: "nearest",
                },
            },
        };
    }
}

export const accountJournalDashboardGraphField = {
    ...journalDashboardGraphField,
    component: AccountJournalDashboardGraphField,
};

registry.category("fields").add("account_journal_dashboard_graph", accountJournalDashboardGraphField);
