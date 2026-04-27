import { components, constants } from "@odoo/o-spreadsheet";
import { _t } from "@web/core/l10n/translation";

const { ChartWithAxisDesignPanel } = components;
const { CHART_AXIS_CHOICES } = constants;

export class OdooChartWithAxisDesignPanel extends ChartWithAxisDesignPanel {
    static template = "spreadsheet_edition.OdooChartWithAxisDesignPanel";

    axisChoices = CHART_AXIS_CHOICES;

    get axesList() {
        return [
            { id: "x", name: _t("Horizontal axis") },
            { id: "y", name: _t("Vertical axis") },
        ];
    }

    updateVerticalAxisPosition(verticalAxisPosition) {
        this.props.updateChart(this.props.figureId, {
            verticalAxisPosition,
        });
    }

    toggleDataTrend(display) {
        const trend = {
            type: "polynomial",
            order: 1,
            ...this.props.definition.trend,
            display,
        };
        this.props.updateChart(this.props.figureId, { trend });
    }

    getTrendLineConfiguration() {
        return this.props.definition.trend;
    }

    getTrendType(config) {
        if (!config) {
            return "";
        }
        return config.type === "polynomial" && config.order === 1 ? "linear" : config.type;
    }

    onChangeTrendType(ev) {
        const type = ev.target.value;
        let config;
        switch (type) {
            case "linear":
            case "polynomial":
                config = {
                    type: "polynomial",
                    order: type === "linear" ? 1 : 2,
                };
                break;
            case "exponential":
            case "logarithmic":
                config = { type };
                break;
            default:
                return;
        }
        this.updateTrendLineValue(config);
    }

    onChangePolynomialDegree(ev) {
        const element = ev.target;
        const order = parseInt(element.value || "1");
        if (order < 2) {
            element.value = `${this.getTrendLineConfiguration()?.order ?? 2}`;
            return;
        }
        this.updateTrendLineValue({ order });
    }

    updateTrendLineValue(config) {
        const trend = {
            ...this.props.definition.trend,
            ...config,
        };
        this.props.updateChart(this.props.figureId, { trend });
    }
}
