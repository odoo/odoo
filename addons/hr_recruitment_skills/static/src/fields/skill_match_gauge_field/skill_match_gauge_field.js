import { getCSSVariableValue } from "@html_editor/utils/formatting";
import { onWillStart } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { formatFloat } from "@web/views/fields/formatters";
import { GaugeField, gaugeField } from "@web/views/fields/gauge/gauge_field";

export class SkillMatchGaugeField extends GaugeField {
    static template = "hr_recruitment.SkillMatchGaugeField";

    setup() {
        super.setup();

        this.orm = useService("orm");

        onWillStart(async () => {
            const matching_job_id = this.props.record.evalContext.context.matching_job_id;
            if (matching_job_id) {
                const matching_job = await this.orm.read("hr.job", [matching_job_id], ["name"]);
                this.matching_job_name = matching_job[0].name;
            }
        });
    }

    get formattedValue() {
        return formatFloat(this.props.record.data[this.props.name], {
            humanReadable: true,
            decimals: 0,
        });
    }

    renderChart() {
        const gaugeValue = this.props.record.data[this.props.name];
        let maxValue = this.props.maxValueField
            ? this.props.record.data[this.props.maxValueField]
            : this.props.maxValue;

        const fgColor =
            gaugeValue > maxValue
                ? getCSSVariableValue("success", getComputedStyle(document.documentElement))
                : getCSSVariableValue("primary", getComputedStyle(document.documentElement));
        maxValue = Math.max(gaugeValue, maxValue);
        if (gaugeValue === 0 && maxValue === 0) {
            maxValue = 1;
        }
        const config = {
            type: "doughnut",
            data: {
                datasets: [
                    {
                        data: [gaugeValue, maxValue - gaugeValue],
                        backgroundColor: [fgColor, "#dddddd"],
                        label: this.title,
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
                    intersect: false,
                    mode: "dataset",
                },
                plugins: {
                    title: {
                        display: false,
                    },
                    tooltip: {
                        displayColors: false,
                        callbacks: {
                            title: (tooltipItem) => false,
                            label: (tooltipItem) =>
                                tooltipItem.dataIndex === 0 &&
                                _t("This score reflects skills and degree match"),
                        },
                    },
                },
                aspectRatio: 2,
            },
        };
        this.chart = new Chart(this.canvasRef.el, config);
    }
}

export const skillMatchGaugeField = {
    ...gaugeField,
    component: SkillMatchGaugeField,
};

registry.category("fields").add("skill_match_gauge_field", skillMatchGaugeField);
