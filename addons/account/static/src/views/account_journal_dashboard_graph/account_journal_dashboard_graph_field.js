import { cookie } from "@web/core/browser/cookie";
import { getCustomColor } from "@web/core/colors/colors";
import { registry } from "@web/core/registry";
import {
    JournalDashboardGraphField,
    journalDashboardGraphField,
} from "@web/views/fields/journal_dashboard_graph/journal_dashboard_graph_field";

const colorScheme = cookie.get("color_scheme");
const GRAPH_GRID_COLOR = getCustomColor(colorScheme, "#d8dadd", "#3A3B41");
const GRAPH_LABEL_COLOR = getCustomColor(colorScheme, "#111827", "#E4E4E5");

export class AccountJournalDashboardGraphField extends JournalDashboardGraphField {
    getBarChartConfig() {
        if (this.data[0].type !== "monthly_paid_unpaid") {
            return super.getBarChartConfig();
        }

        return this.getMonthlyPaidUnpaidChartConfig();
    }

    getMonthlyPaidUnpaidChartConfig() {
        const paidColor = "#875A7B";
        const unpaidColor = "#DEC7D6";

        return {
            type: "bar",
            data: {
                labels: this.data[0].labels,
                datasets: [
                    {
                        backgroundColor: paidColor,
                        data: this.data[0].paid_values,
                        label: this.data[0].paid_key,
                        stack: "invoice_status",
                        borderWidth: 0,
                    },
                    {
                        backgroundColor: unpaidColor,
                        data: this.data[0].unpaid_values,
                        label: this.data[0].unpaid_key,
                        stack: "invoice_status",
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
                        stacked: true,
                    },
                    x: {
                        stacked: true,
                        grid: {
                            color: GRAPH_GRID_COLOR,
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
