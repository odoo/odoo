import { getCSSVariableValue } from "@html_editor/utils/formatting";
import { Component, onWillStart } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useLayoutEffect, useRef } from "@web/owl2/utils";
import { formatFloat } from "@web/views/fields/formatters";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

const CHART_COLORS = [
    "#1f77b4",
    "#9467bd",
    "#2ca02c",
    "#ff7f0e",
    "#17becf",
    "#8c564b",
];

export class GaugeChartWidget extends Component {
    static template = "hr_recruitment.GaugeChartWidget";
    static props = {
        ...standardWidgetProps,
        scoreFields: { type: String, optional: true },
        maxValue: { type: Number, optional: true },
        maxValueField: { type: String, optional: true },
        title: { type: String, optional: true },
    };

    setup() {
        this.chart = null;
        this.matchingJobName = null;
        this.canvasRef = useRef("canvas");
        this.orm = useService("orm");

        onWillStart(async () => {
            await loadBundle("web.chartjs_lib");
            const matchingJobId = this.props.record.evalContext.context.matching_job_id;
            if (matchingJobId) {
                const [matchingJob] = await this.orm.read("hr.job", [matchingJobId], ["name"]);
                this.matchingJobName = matchingJob?.name;
            }
        });

        useLayoutEffect(() => {
            this.renderChart();
            return () => {
                if (this.chart) {
                    this.chart.destroy();
                }
            };
        });
    }

    get chartTitle() {
        return this.props.title || _t("Job Position Matching");
    }

    get configuredScoreFields() {
        return (this.props.scoreFields || "")
            .split(",")
            .map((fieldName) => fieldName.trim())
            .filter(Boolean);
    }

    get scoreSegments() {
        return this.configuredScoreFields.map((fieldName) => {
            const value = Math.max(0, Number(this.props.record.data[fieldName]) || 0);
            return {
                fieldName,
                label: this.props.record.fields[fieldName]?.string || fieldName,
                value,
                isRemainder: false,
            };
        });
    }

    get resolvedMaxValue() {
        const maxFromField = this.props.maxValueField
            ? Number(this.props.record.data[this.props.maxValueField])
            : NaN;
        if (Number.isFinite(maxFromField)) {
            return Math.max(0, maxFromField);
        }
        if (Number.isFinite(this.props.maxValue)) {
            return Math.max(0, this.props.maxValue);
        }
        return 100;
    }

    get totalScore() {
        return this.scoreSegments.reduce((total, segment) => total + segment.value, 0);
    }

    get chartTotal() {
        return Math.max(this.resolvedMaxValue, this.totalScore, 1);
    }

    get remainderValue() {
        return Math.max(0, this.chartTotal - this.totalScore);
    }

    get chartSegments() {
        return [
            ...this.scoreSegments,
            {
                fieldName: "__remaining__",
                label: _t("Remaining"),
                value: this.remainderValue,
                isRemainder: true,
            },
        ];
    }

    formatPercent(value) {
        return `${formatFloat(value, { humanReadable: true, decimals: 0 })}%`;
    }

    getSegmentColor(segment, index) {
        if (segment.isRemainder) {
            return "#dddddd";
        }
        const color = CHART_COLORS[index % CHART_COLORS.length];
        if (index === 0) {
            return getCSSVariableValue("primary", getComputedStyle(document.documentElement));
        }
        return color;
    }

    renderChart() {
        const segments = this.chartSegments;
        const values = segments.map((segment) => segment.value);
        const backgroundColor = segments.map((segment, index) => this.getSegmentColor(segment, index));

        const config = {
            type: "doughnut",
            data: {
                datasets: [
                    {
                        data: values,
                        backgroundColor,
                        label: this.chartTitle,
                    },
                ],
            },
            options: {
                circumference: 180,
                rotation: 270,
                responsive: true,
                maintainAspectRatio: false,
                cutout: "50%",
                interaction: {
                    intersect: true,
                    mode: "nearest",
                },
                plugins: {
                    title: {
                        display: false,
                    },
                    tooltip: {
                        displayColors: false,
                        callbacks: {
                            title: () => false,
                            label: (tooltipItem) => {
                                const segment = segments[tooltipItem.dataIndex];
                                return `${segment.label}: ${this.formatPercent(segment.value)}`;
                            },
                        },
                    },
                },
                aspectRatio: 2,
            },
        };
        this.chart = new Chart(this.canvasRef.el, config);
    }
}

export const gaugeChartWidget = {
    component: GaugeChartWidget,
    extractProps: ({ attrs }) => {
        const maxValue = Number(attrs.max_value);
        return {
            scoreFields: attrs.score_fields,
            maxValue: Number.isFinite(maxValue) ? maxValue : undefined,
            maxValueField: attrs.max_value_field,
            title: attrs.title,
        };
    },
    supportedAttributes: [
        {
            label: _t("Score Fields"),
            name: "score_fields",
            type: "string",
        },
        {
            label: _t("Max Value"),
            name: "max_value",
            type: "string",
        },
        {
            label: _t("Max Value Field"),
            name: "max_value_field",
            type: "field",
            availableTypes: ["integer", "float"],
        },
        {
            label: _t("Title"),
            name: "title",
            type: "string",
        },
    ],
};

registry.category("view_widgets").add("gauge_chart", gaugeChartWidget);
