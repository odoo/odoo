import { loadBundle } from "@web/core/assets";
import { cookie } from "@web/core/browser/cookie";
import { getColor } from "@web/core/colors/colors";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { Component, onWillStart, useEffect, useRef } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class JsonPopOver extends Component {
    static template = "";
    static props = {...standardFieldProps};
    get jsonValue() {
        return JSON.parse(this.props.record.data[this.props.name]);
    }
}

export const jsonPopOver = {
    component: JsonPopOver,
    displayName: _t("Json Popup"),
    supportedTypes: ["char"],
};

// --------------------------------------------------------------------------
// Lead Days
// --------------------------------------------------------------------------

export class PopOverLeadDays extends JsonPopOver {
    static template = "stock.leadDays";
}

export const popOverLeadDays = {
    ...jsonPopOver,
    component: PopOverLeadDays,
};
registry.category("fields").add("lead_days_widget", popOverLeadDays);

// --------------------------------------------------------------------------
// Forecast Graph
// --------------------------------------------------------------------------

export class ReplenishmentGraphWidget extends JsonPopOver {
    static template = "stock.replenishmentGraph";
    setup() {
        super.setup();
        this.chart = null;
        this.canvasRef = useRef("canvas");
        onWillStart(async () => {
            this.displayUOM = await user.hasGroup("uom.group_uom");
            await loadBundle("web.chartjs_lib");
        });

        useEffect(() => {
            this.renderChart();
            return () => {
                if (this.chart) {
                    this.chart.destroy();
                }
            };
        });
    }
    get productUomName(){
        return this.jsonValue["product_uom_name"];
    }
    get qtyOnHand(){
        return this.jsonValue["qty_on_hand"];
    }
    get productMaxQty() {
        return this.jsonValue["product_max_qty"];
    }
    get productMinQty() {
        return this.jsonValue["product_min_qty"];
    }
    get dailyDemand() {
        return this.jsonValue["daily_demand"];
    }
    get averageStock() {
        return this.jsonValue["average_stock"];
    }
    get orderingPeriod() {
        return this.jsonValue["ordering_period"];
    }
    get qtiesAreTheSame() {
        return this.productMinQty === this.productMaxQty;
    }
    get leadTime() {
        return this.jsonValue["lead_time"];
    }

    renderChart() {
        if (this.chart) {
            this.chart.destroy();
        }
        const config = this.getScatterGraphConfig();
        this.chart = new Chart(this.canvasRef.el, config);
    }

    getScatterGraphConfig() {
        const dashLine = (ctx, value) => ctx.p1.raw.x === this.jsonValue['x_axis_vals'].slice(-1)[0] ? value : undefined;
        const pushYLabels = (ticks) => ticks.push({value: this.productMinQty}, {value: this.productMaxQty});
        const showYLabel = (tick) => tick === this.productMinQty || tick === this.productMaxQty ? tick : '';
        const labels = this.jsonValue['x_axis_vals'];
        const maxLineColor = getColor(1, cookie.get("color_scheme"), "odoo");
        const minLineColor = getColor(2, cookie.get("color_scheme"), "odoo");
        const curveLineColor = getColor(3, cookie.get("color_scheme"), "odoo");
        return {
            type: "scatter",
            data: {
                labels,
                datasets: [{
                    type: "line",
                    data: this.jsonValue["max_line_vals"],
                    fill: false,
                    pointStyle: false,
                    borderColor: maxLineColor,
                }, {
                    type: "line",
                    data: this.jsonValue["min_line_vals"],
                    fill: false,
                    pointStyle: false,
                    borderColor: minLineColor,
                }, {
                    type: "line",
                    data: this.jsonValue["curve_line_vals"],
                    fill: false,
                    pointStyle: false,
                    borderColor: curveLineColor,
                    segment: {
                        borderDash: ctx => dashLine(ctx, [6, 6]),
                    }
                }],
            },
            options: {
                maintainAspectRatio: false,
                showLine: true,
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: false },
                },
                scales: {
                    y: {
                        grid: {display: false},
                        beforeTickToLabelConversion: data => pushYLabels(data.ticks),
                        ticks: {
                            autoSkip: false,
                            callback: tick => showYLabel(tick),
                        },
                        suggestedMax: this.productMaxQty * 1.1,
                        suggestedMin: this.productMinQty * 0.9,
                    },
                    x: {
                        type: 'category',
                        grid: {display: false},
                    },
                },
            },
        }
    }
}

export const replenishmentGraphWidget = {
    ...jsonPopOver,
    component: ReplenishmentGraphWidget,
};

registry.category("fields").add("replenishment_graph_widget", replenishmentGraphWidget);
