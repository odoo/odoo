/** @odoo-module **/

import { Component, useChildSubEnv, useState } from "@odoo/owl";
import { cn } from "@odx_owl/core/utils/cn";
import { isChartSeries, isObjectOrEmpty } from "@odx_owl/core/utils/prop_validators";

const CHART_VIEWBOX_WIDTH = 600;
const CHART_DONUT_SIZE = 240;
const CHART_PALETTE = [
    "hsl(var(--odx-chart-1))",
    "hsl(var(--odx-chart-2))",
    "hsl(var(--odx-chart-3))",
    "hsl(var(--odx-chart-4))",
    "hsl(var(--odx-chart-5))",
];

function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
}

function formatLabel(value) {
    return String(value || "")
        .replace(/[_-]+/g, " ")
        .replace(/\b\w/g, (char) => char.toUpperCase());
}

function getNumber(value) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
}

function resolveSeriesKeys(data, series, xKey, config = {}) {
    if (Array.isArray(series) && series.length) {
        return series.map((item) => (typeof item === "string" ? item : item?.key)).filter(Boolean);
    }
    const configKeys = Object.keys(config || {});
    if (configKeys.length) {
        return configKeys;
    }
    const sample = Array.isArray(data) ? data[0] || {} : {};
    return Object.keys(sample).filter(
        (key) =>
            key !== xKey &&
            (data || []).some((row) => Number.isFinite(Number(row?.[key])))
    );
}

function getSeriesEntry(config, key, index = 0) {
    const item = config?.[key] || {};
    return {
        key,
        label: item.label || formatLabel(key),
        color: item.color || CHART_PALETTE[index % CHART_PALETTE.length],
    };
}

function polarToCartesian(cx, cy, radius, angle) {
    const radians = ((angle - 90) * Math.PI) / 180;
    return {
        x: cx + radius * Math.cos(radians),
        y: cy + radius * Math.sin(radians),
    };
}

function describeArc(cx, cy, outerRadius, innerRadius, startAngle, endAngle) {
    const startOuter = polarToCartesian(cx, cy, outerRadius, endAngle);
    const endOuter = polarToCartesian(cx, cy, outerRadius, startAngle);
    const startInner = polarToCartesian(cx, cy, innerRadius, endAngle);
    const endInner = polarToCartesian(cx, cy, innerRadius, startAngle);
    const largeArcFlag = endAngle - startAngle > 180 ? 1 : 0;

    return [
        `M ${startOuter.x} ${startOuter.y}`,
        `A ${outerRadius} ${outerRadius} 0 ${largeArcFlag} 0 ${endOuter.x} ${endOuter.y}`,
        `L ${endInner.x} ${endInner.y}`,
        `A ${innerRadius} ${innerRadius} 0 ${largeArcFlag} 1 ${startInner.x} ${startInner.y}`,
        "Z",
    ].join(" ");
}

class ChartBase extends Component {
    get chartHeight() {
        return Math.max(160, Number(this.props.height) || 240);
    }

    get innerHeight() {
        return this.chartHeight - this.padding.top - this.padding.bottom;
    }

    get innerWidth() {
        return CHART_VIEWBOX_WIDTH - this.padding.left - this.padding.right;
    }

    get padding() {
        return {
            top: 20,
            right: 18,
            bottom: 30,
            left: 18,
        };
    }

    get seriesKeys() {
        return resolveSeriesKeys(
            this.props.data,
            this.props.series,
            this.props.xKey,
            this.env.odxChart.config
        );
    }

    get seriesEntries() {
        return this.seriesKeys.map((key, index) => this.env.odxChart.getSeriesEntry(key, index));
    }

    get viewBox() {
        return `0 0 ${CHART_VIEWBOX_WIDTH} ${this.chartHeight}`;
    }

    get chartStyle() {
        return `height: ${this.chartHeight}px;`;
    }

    get yDomain() {
        const values = [];
        for (const row of this.props.data || []) {
            for (const key of this.seriesKeys) {
                values.push(getNumber(row[key]));
            }
        }
        const max = values.length ? Math.max(...values) : 0;
        const min = values.length ? Math.min(...values) : 0;
        const lower = this.props.min !== undefined ? getNumber(this.props.min) : Math.min(0, min);
        let upper = this.props.max !== undefined ? getNumber(this.props.max) : max;
        if (upper === lower) {
            upper = lower + 1;
        }
        return { min: lower, max: upper };
    }

    get axisTicks() {
        const ticks = [];
        const count = 4;
        const { min, max } = this.yDomain;
        for (let index = 0; index < count; index++) {
            const ratio = index / (count - 1);
            const value = max - ratio * (max - min);
            ticks.push({
                key: `tick-${index}`,
                value,
                y: this.scaleY(value),
                label: Number.isInteger(value) ? String(value) : value.toFixed(1),
            });
        }
        return ticks;
    }

    get categories() {
        const data = this.props.data || [];
        const step = data.length > 1 ? this.innerWidth / (data.length - 1) : 0;
        return data.map((row, index) => ({
            index,
            label: row[this.props.xKey] ?? `Item ${index + 1}`,
            row,
            x: data.length === 1 ? this.padding.left + this.innerWidth / 2 : this.padding.left + step * index,
        }));
    }

    getTooltipPayload(index, target) {
        const row = (this.props.data || [])[index];
        if (!row || !target) {
            return null;
        }
        const rect = target.getBoundingClientRect();
        return {
            x: rect.left + rect.width / 2,
            y: rect.top - 10,
            label: row[this.props.xKey] ?? `Item ${index + 1}`,
            items: this.seriesEntries.map((entry, entryIndex) => ({
                key: entry.key,
                label: entry.label,
                color: entry.color,
                value: getNumber(row[this.seriesKeys[entryIndex]]),
            })),
        };
    }

    scaleY(value) {
        const { min, max } = this.yDomain;
        const ratio = (getNumber(value) - min) / (max - min);
        return this.padding.top + this.innerHeight - ratio * this.innerHeight;
    }

    showTooltip(index, ev) {
        const tooltip = this.getTooltipPayload(index, ev.currentTarget);
        if (tooltip) {
            this.env.odxChart.setTooltip(tooltip);
        }
    }

    hideTooltip() {
        this.env.odxChart.clearTooltip();
    }
}

export class ChartContainer extends Component {
    static template = "odx_owl.ChartContainer";
    static props = {
        className: { type: String, optional: true },
        config: { optional: true, validate: isObjectOrEmpty },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        config: {},
        tag: "div",
    };

    setup() {
        const self = this;
        this.state = useState({
            tooltip: null,
        });

        useChildSubEnv({
            odxChart: {
                clearTooltip: () => self.clearTooltip(),
                get config() {
                    return self.props.config || {};
                },
                getSeriesEntries: (series) => self.getSeriesEntries(series),
                getSeriesEntry: (key, index) => self.getSeriesEntry(key, index),
                getTooltip: () => self.state.tooltip,
                setTooltip: (tooltip) => self.setTooltip(tooltip),
            },
        });
    }

    get classes() {
        return cn("odx-chart", this.props.className);
    }

    clearTooltip() {
        this.state.tooltip = null;
    }

    getSeriesEntries(series = []) {
        const config = this.props.config || {};
        const keys = Array.isArray(series) && series.length ? series : Object.keys(config);
        return keys
            .map((item, index) =>
                typeof item === "string" ? this.getSeriesEntry(item, index) : {
                    key: item.key || `series-${index}`,
                    label: item.label || formatLabel(item.key || item.label || `Series ${index + 1}`),
                    color: item.color || CHART_PALETTE[index % CHART_PALETTE.length],
                }
            )
            .filter((item) => item.key);
    }

    getSeriesEntry(key, index = 0) {
        return getSeriesEntry(this.props.config || {}, key, index);
    }

    setTooltip(tooltip) {
        this.state.tooltip = tooltip;
    }
}

export class ChartLegend extends Component {
    static template = "odx_owl.ChartLegend";
    static props = {
        className: { type: String, optional: true },
        orientation: { type: String, optional: true },
        series: { optional: true, validate: isChartSeries },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        className: "",
        orientation: "horizontal",
        series: [],
    };

    get classes() {
        return cn(
            "odx-chart-legend",
            {
                "odx-chart-legend--horizontal": this.props.orientation !== "vertical",
                "odx-chart-legend--vertical": this.props.orientation === "vertical",
            },
            this.props.className
        );
    }

    get entries() {
        return this.env.odxChart.getSeriesEntries(this.props.series);
    }
}

export class ChartLegendContent extends Component {
    static template = "odx_owl.ChartLegendContent";
    static props = {
        className: { type: String, optional: true },
        series: { optional: true, validate: isChartSeries },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        series: [],
        tag: "div",
    };

    get classes() {
        return cn("odx-chart-legend__content", this.props.className);
    }

    get entries() {
        return this.env.odxChart.getSeriesEntries(this.props.series);
    }
}

ChartLegend.components = {
    ChartLegendContent,
};

export class ChartTooltip extends Component {
    static template = "odx_owl.ChartTooltip";
    static props = {
        className: { type: String, optional: true },
        formatter: { type: Function, optional: true },
        hideLabel: { type: Boolean, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        className: "",
        formatter: undefined,
        hideLabel: false,
    };

    get classes() {
        return cn("odx-chart-tooltip", this.props.className);
    }

    get style() {
        const tooltip = this.tooltip;
        if (!tooltip) {
            return "";
        }
        return `left: ${Math.round(tooltip.x)}px; top: ${Math.round(tooltip.y)}px;`;
    }

    get tooltip() {
        return this.env.odxChart.getTooltip();
    }

    get visible() {
        return Boolean(this.tooltip?.items?.length);
    }

    formatItem(item) {
        if (this.props.formatter) {
            return this.props.formatter(item.value, item);
        }
        return Number.isInteger(item.value) ? String(item.value) : item.value.toFixed(1);
    }
}

export class ChartTooltipContent extends Component {
    static template = "odx_owl.ChartTooltipContent";
    static props = {
        className: { type: String, optional: true },
        formatter: { type: Function, optional: true },
        hideLabel: { type: Boolean, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        formatter: undefined,
        hideLabel: false,
        tag: "div",
    };

    get classes() {
        return cn("odx-chart-tooltip__content", this.props.className);
    }

    get tooltip() {
        return this.env.odxChart.getTooltip();
    }

    formatItem(item) {
        if (this.props.formatter) {
            return this.props.formatter(item.value, item);
        }
        return Number.isInteger(item.value) ? String(item.value) : item.value.toFixed(1);
    }
}

ChartTooltip.components = {
    ChartTooltipContent,
};

export class LineChart extends ChartBase {
    static template = "odx_owl.LineChart";
    static props = {
        ariaLabel: { type: String, optional: true },
        className: { type: String, optional: true },
        data: { type: Array, optional: true },
        height: { type: Number, optional: true },
        max: { type: Number, optional: true },
        min: { type: Number, optional: true },
        series: { optional: true, validate: isChartSeries },
        showDots: { type: Boolean, optional: true },
        showGrid: { type: Boolean, optional: true },
        xKey: { type: String, optional: true },
    };
    static defaultProps = {
        ariaLabel: "Line chart",
        className: "",
        data: [],
        height: 240,
        series: [],
        showDots: true,
        showGrid: true,
        xKey: "label",
    };

    get classes() {
        return cn("odx-chart__surface", "odx-chart__surface--line", this.props.className);
    }

    get lineSeries() {
        return this.seriesEntries.map((entry, entryIndex) => {
            const points = this.categories.map((category) => ({
                key: `${entry.key}-${category.index}`,
                x: category.x,
                y: this.scaleY(category.row[entry.key]),
                value: getNumber(category.row[entry.key]),
            }));
            const path = points
                .map((point, index) => `${index ? "L" : "M"} ${point.x} ${point.y}`)
                .join(" ");
            return {
                ...entry,
                path,
                points,
            };
        });
    }

    get hotspots() {
        const width = this.categories.length > 1 ? this.innerWidth / (this.categories.length - 1) : this.innerWidth;
        return this.categories.map((category) => ({
            key: `line-hotspot-${category.index}`,
            index: category.index,
            label: category.label,
            x: category.x - width / 2,
            width,
        }));
    }
}

export class BarChart extends ChartBase {
    static template = "odx_owl.BarChart";
    static props = LineChart.props;
    static defaultProps = {
        ...LineChart.defaultProps,
        ariaLabel: "Bar chart",
    };

    get classes() {
        return cn("odx-chart__surface", "odx-chart__surface--bar", this.props.className);
    }

    get barGroups() {
        const data = this.props.data || [];
        const step = data.length ? this.innerWidth / data.length : this.innerWidth;
        const groupWidth = step * 0.72;
        const gap = 8;
        const barWidth = this.seriesEntries.length
            ? Math.max(10, (groupWidth - gap * (this.seriesEntries.length - 1)) / this.seriesEntries.length)
            : groupWidth;
        const baseline = this.scaleY(0);

        return data.map((row, index) => {
            const center = this.padding.left + step * index + step / 2;
            const startX = center - groupWidth / 2;
            const bars = this.seriesEntries.map((entry, entryIndex) => {
                const value = getNumber(row[entry.key]);
                const y = value >= 0 ? this.scaleY(value) : baseline;
                const height = Math.abs(baseline - this.scaleY(value));
                return {
                    key: `${entry.key}-${index}`,
                    color: entry.color,
                    height,
                    value,
                    width: barWidth,
                    x: startX + entryIndex * (barWidth + gap),
                    y,
                };
            });

            return {
                key: `bar-group-${index}`,
                bars,
                hotspotWidth: step,
                index,
                label: row[this.props.xKey] ?? `Item ${index + 1}`,
                x: center - step / 2,
                xLabel: center,
            };
        });
    }
}

export class DonutChart extends Component {
    static template = "odx_owl.DonutChart";
    static props = {
        ariaLabel: { type: String, optional: true },
        className: { type: String, optional: true },
        data: { type: Array, optional: true },
        height: { type: Number, optional: true },
        nameKey: { type: String, optional: true },
        valueKey: { type: String, optional: true },
    };
    static defaultProps = {
        ariaLabel: "Donut chart",
        className: "",
        data: [],
        height: CHART_DONUT_SIZE,
        nameKey: "name",
        valueKey: "value",
    };

    get center() {
        return CHART_DONUT_SIZE / 2;
    }

    get classes() {
        return cn("odx-chart__surface", "odx-chart__surface--donut", this.props.className);
    }

    get slices() {
        const total = (this.props.data || []).reduce(
            (sum, item) => sum + Math.max(0, getNumber(item[this.props.valueKey])),
            0
        );
        let angle = 0;
        return (this.props.data || []).map((item, index) => {
            const key = item[this.props.nameKey] || `slice-${index}`;
            const value = Math.max(0, getNumber(item[this.props.valueKey]));
            const percent = total ? value / total : 0;
            const sweep = percent * 360;
            const startAngle = angle;
            const endAngle = angle + sweep;
            angle = endAngle;
            const entry = this.env.odxChart.getSeriesEntry(key, index);
            return {
                color: entry.color,
                key,
                label: entry.label,
                path: describeArc(this.center, this.center, 92, 56, startAngle, endAngle || startAngle + 0.01),
                percent,
                value,
            };
        });
    }

    get total() {
        return this.slices.reduce((sum, slice) => sum + slice.value, 0);
    }

    get viewBox() {
        return `0 0 ${CHART_DONUT_SIZE} ${CHART_DONUT_SIZE}`;
    }

    get chartStyle() {
        return `height: ${Math.max(180, Number(this.props.height) || CHART_DONUT_SIZE)}px;`;
    }

    showSliceTooltip(slice, ev) {
        const rect = ev.currentTarget.getBoundingClientRect();
        this.env.odxChart.setTooltip({
            x: rect.left + rect.width / 2,
            y: rect.top - 10,
            label: slice.label,
            items: [
                {
                    key: slice.key,
                    label: slice.label,
                    color: slice.color,
                    value: slice.value,
                },
            ],
        });
    }

    hideTooltip() {
        this.env.odxChart.clearTooltip();
    }
}

export class AreaChart extends ChartBase {
    static template = "odx_owl.AreaChart";
    static props = {
        ariaLabel: { type: String, optional: true },
        className: { type: String, optional: true },
        data: { type: Array, optional: true },
        gradient: { type: Boolean, optional: true },
        height: { type: Number, optional: true },
        max: { type: Number, optional: true },
        min: { type: Number, optional: true },
        series: { optional: true, validate: isChartSeries },
        showDots: { type: Boolean, optional: true },
        showGrid: { type: Boolean, optional: true },
        stacked: { type: Boolean, optional: true },
        xKey: { type: String, optional: true },
    };
    static defaultProps = {
        ariaLabel: "Area chart",
        className: "",
        data: [],
        gradient: true,
        height: 240,
        series: [],
        showDots: true,
        showGrid: true,
        stacked: false,
        xKey: "label",
    };

    get classes() {
        return cn("odx-chart__surface", "odx-chart__surface--area", this.props.className);
    }

    get areaSeries() {
        const baseline = this.scaleY(0);
        let stackedValues = this.props.stacked
            ? this.categories.map(() => 0)
            : null;

        return this.seriesEntries.map((entry, entryIndex) => {
            const points = this.categories.map((category, index) => {
                let value = getNumber(category.row[entry.key]);
                if (this.props.stacked && stackedValues) {
                    const prevValue = stackedValues[index];
                    stackedValues[index] += value;
                    value = stackedValues[index];
                    return {
                        key: `${entry.key}-${category.index}`,
                        x: category.x,
                        y: this.scaleY(value),
                        baseY: this.scaleY(prevValue),
                        value,
                    };
                }
                return {
                    key: `${entry.key}-${category.index}`,
                    x: category.x,
                    y: this.scaleY(value),
                    baseY: baseline,
                    value: getNumber(category.row[entry.key]),
                };
            });

            const linePath = points
                .map((point, index) => `${index ? "L" : "M"} ${point.x} ${point.y}`)
                .join(" ");

            const areaPath = [
                linePath,
                ...points
                    .slice()
                    .reverse()
                    .map((point, index) =>
                        `${index ? "L" : ""} ${point.x} ${point.baseY}`
                    ),
                "Z",
            ].join(" ");

            return {
                ...entry,
                areaPath,
                linePath,
                points,
                gradientId: this.props.gradient ? `area-gradient-${entry.key}-${entryIndex}` : null,
            };
        });
    }

    get hotspots() {
        const width = this.categories.length > 1 ? this.innerWidth / (this.categories.length - 1) : this.innerWidth;
        return this.categories.map((category) => ({
            key: `area-hotspot-${category.index}`,
            index: category.index,
            label: category.label,
            x: category.x - width / 2,
            width,
        }));
    }
}

export class RadarChart extends Component {
    static template = "odx_owl.RadarChart";
    static props = {
        ariaLabel: { type: String, optional: true },
        className: { type: String, optional: true },
        data: { type: Array, optional: true },
        gridType: { type: String, optional: true },
        height: { type: Number, optional: true },
        levels: { type: Number, optional: true },
        series: { optional: true, validate: isChartSeries },
        showDots: { type: Boolean, optional: true },
        showGrid: { type: Boolean, optional: true },
        xKey: { type: String, optional: true },
    };
    static defaultProps = {
        ariaLabel: "Radar chart",
        className: "",
        data: [],
        gridType: "polygon",
        height: 300,
        levels: 5,
        series: [],
        showDots: true,
        showGrid: true,
        xKey: "label",
    };

    get classes() {
        return cn("odx-chart__surface", "odx-chart__surface--radar", this.props.className);
    }

    get chartHeight() {
        return Math.max(200, Number(this.props.height) || 300);
    }

    get center() {
        return CHART_VIEWBOX_WIDTH / 2;
    }

    get radius() {
        return (Math.min(CHART_VIEWBOX_WIDTH, this.chartHeight) * 0.38);
    }

    get viewBox() {
        return `0 0 ${CHART_VIEWBOX_WIDTH} ${this.chartHeight}`;
    }

    get chartStyle() {
        return `height: ${this.chartHeight}px;`;
    }

    get seriesKeys() {
        return resolveSeriesKeys(
            this.props.data,
            this.props.series,
            this.props.xKey,
            this.env.odxChart.config
        );
    }

    get seriesEntries() {
        return this.seriesKeys.map((key, index) => this.env.odxChart.getSeriesEntry(key, index));
    }

    get categories() {
        const data = this.props.data || [];
        return data.map((row, index) => {
            const angle = (index * 360) / data.length;
            const point = polarToCartesian(this.center, this.center, this.radius, angle);
            return {
                index,
                label: row[this.props.xKey] ?? `Item ${index + 1}`,
                row,
                angle,
                x: point.x,
                y: point.y,
            };
        });
    }

    get maxValue() {
        const values = [];
        for (const row of this.props.data || []) {
            for (const key of this.seriesKeys) {
                values.push(getNumber(row[key]));
            }
        }
        return values.length ? Math.max(...values, 1) : 1;
    }

    get gridLevels() {
        const levels = Math.max(1, this.props.levels || 5);
        const result = [];
        for (let i = 1; i <= levels; i++) {
            const levelRadius = (this.radius * i) / levels;
            if (this.props.gridType === "circle") {
                result.push({
                    key: `grid-circle-${i}`,
                    type: "circle",
                    cx: this.center,
                    cy: this.center,
                    r: levelRadius,
                });
            } else {
                const points = this.categories
                    .map((cat) => {
                        const point = polarToCartesian(this.center, this.center, levelRadius, cat.angle);
                        return `${point.x},${point.y}`;
                    })
                    .join(" ");
                result.push({
                    key: `grid-polygon-${i}`,
                    type: "polygon",
                    points,
                });
            }
        }
        return result;
    }

    get axes() {
        return this.categories.map((cat) => ({
            key: `axis-${cat.index}`,
            x1: this.center,
            y1: this.center,
            x2: cat.x,
            y2: cat.y,
            labelX: cat.x + (cat.x - this.center) * 0.15,
            labelY: cat.y + (cat.y - this.center) * 0.15,
            label: cat.label,
        }));
    }

    get radarSeries() {
        const max = this.maxValue;
        return this.seriesEntries.map((entry) => {
            const points = this.categories.map((cat) => {
                const value = getNumber(cat.row[entry.key]);
                const ratio = Math.max(0, Math.min(1, value / max));
                const point = polarToCartesian(this.center, this.center, this.radius * ratio, cat.angle);
                return {
                    key: `${entry.key}-${cat.index}`,
                    x: point.x,
                    y: point.y,
                    value,
                };
            });
            const polygonPoints = points.map((p) => `${p.x},${p.y}`).join(" ");
            return {
                ...entry,
                points,
                polygonPoints,
            };
        });
    }

    showTooltip(categoryIndex, seriesIndex, ev) {
        const row = (this.props.data || [])[categoryIndex];
        if (!row) {
            return;
        }
        const rect = ev.currentTarget.getBoundingClientRect();
        this.env.odxChart.setTooltip({
            x: rect.left + rect.width / 2,
            y: rect.top - 10,
            label: row[this.props.xKey] ?? `Item ${categoryIndex + 1}`,
            items: this.seriesEntries.map((entry, entryIndex) => ({
                key: entry.key,
                label: entry.label,
                color: entry.color,
                value: getNumber(row[this.seriesKeys[entryIndex]]),
            })),
        });
    }

    hideTooltip() {
        this.env.odxChart.clearTooltip();
    }
}

export class RadialChart extends Component {
    static template = "odx_owl.RadialChart";
    static props = {
        ariaLabel: { type: String, optional: true },
        className: { type: String, optional: true },
        data: { type: Array, optional: true },
        endAngle: { type: Number, optional: true },
        height: { type: Number, optional: true },
        innerRadius: { type: Number, optional: true },
        nameKey: { type: String, optional: true },
        showLabel: { type: Boolean, optional: true },
        startAngle: { type: Number, optional: true },
        valueKey: { type: String, optional: true },
    };
    static defaultProps = {
        ariaLabel: "Radial chart",
        className: "",
        data: [],
        endAngle: 360,
        height: 200,
        innerRadius: 60,
        nameKey: "name",
        showLabel: false,
        startAngle: 0,
        valueKey: "value",
    };

    get classes() {
        return cn("odx-chart__surface", "odx-chart__surface--radial", this.props.className);
    }

    get chartHeight() {
        return Math.max(160, Number(this.props.height) || 200);
    }

    get center() {
        return Math.min(CHART_VIEWBOX_WIDTH, this.chartHeight) / 2;
    }

    get viewBox() {
        const size = Math.min(CHART_VIEWBOX_WIDTH, this.chartHeight);
        return `0 0 ${size} ${size}`;
    }

    get chartStyle() {
        return `height: ${this.chartHeight}px;`;
    }

    get maxValue() {
        const values = (this.props.data || []).map((item) =>
            Math.max(0, getNumber(item[this.props.valueKey]))
        );
        return values.length ? Math.max(...values) : 100;
    }

    get rings() {
        const data = this.props.data || [];
        const maxValue = this.maxValue;
        const startAngle = this.props.startAngle || 0;
        const endAngle = this.props.endAngle || 360;
        const totalAngle = endAngle - startAngle;
        const ringCount = data.length;
        if (!ringCount) {
            return [];
        }

        const outerRadius = this.center * 0.85;
        const innerRadiusPercent = clamp(this.props.innerRadius || 60, 0, 100);
        const innerRadiusBase = (outerRadius * innerRadiusPercent) / 100;
        const ringThickness = (outerRadius - innerRadiusBase) / ringCount;

        return data.map((item, index) => {
            const key = item[this.props.nameKey] || `ring-${index}`;
            const value = Math.max(0, getNumber(item[this.props.valueKey]));
            const ratio = maxValue > 0 ? value / maxValue : 0;
            const sweep = ratio * totalAngle;
            const currentInner = innerRadiusBase + index * ringThickness;
            const currentOuter = currentInner + ringThickness;
            const entry = this.env.odxChart.getSeriesEntry(key, index);

            const backgroundPath = describeArc(
                this.center,
                this.center,
                currentOuter,
                currentInner,
                startAngle,
                endAngle
            );
            const valuePath = describeArc(
                this.center,
                this.center,
                currentOuter,
                currentInner,
                startAngle,
                startAngle + sweep
            );

            return {
                key,
                label: entry.label,
                color: entry.color,
                value,
                backgroundPath,
                valuePath,
            };
        });
    }

    get centerValue() {
        if (!this.props.showLabel) {
            return null;
        }
        const total = (this.props.data || []).reduce(
            (sum, item) => sum + Math.max(0, getNumber(item[this.props.valueKey])),
            0
        );
        return Number.isInteger(total) ? String(total) : total.toFixed(1);
    }

    showRingTooltip(ring, ev) {
        const rect = ev.currentTarget.getBoundingClientRect();
        this.env.odxChart.setTooltip({
            x: rect.left + rect.width / 2,
            y: rect.top - 10,
            label: ring.label,
            items: [
                {
                    key: ring.key,
                    label: ring.label,
                    color: ring.color,
                    value: ring.value,
                },
            ],
        });
    }

    hideTooltip() {
        this.env.odxChart.clearTooltip();
    }
}
