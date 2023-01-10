odoo.define("web/static/src/js/views/graph/graph_renderer", function (require) {
    "use strict";

    const AbstractRenderer = require("web.AbstractRendererOwl");
    const { DateClasses } = require("web.dataComparisonUtils");
    const fieldUtils = require("web.field_utils");
    const { sortBy } = require("web.utils");

    const {
        COLORS,
        DEFAULT_BG,
        FORMAT_OPTIONS,
        MAX_LEGEND_LENGTH,
        getColor,
        getMaxWidth,
        hexToRGBA,
        shortenLabel,
    } = require("web/static/src/js/views/graph/graph_utils");

    const { useRef } = owl.hooks;
    class GraphRenderer extends AbstractRenderer {
        constructor() {
            super(...arguments);

            this.noDataLabel = [this.env._t("No data")];
            this.fakeDataLabel = [""];
            this.sampleDataTargets = [".o_graph_canvas_container"];
            this._processProps(this.props);

            this.canvasRef = useRef("canvas");
            this.containerRef = useRef("container");
        }

        async willUpdateProps(nextProps) {
            await super.willUpdateProps(...arguments);
            this._processProps(nextProps);
        }

        mounted() {
            super.mounted();
            this._renderChart();
        }

        patched() {
            super.patched();
            this._renderChart();
        }

        //---------------------------------------------------------------------
        // Getters
        //---------------------------------------------------------------------

        get measureDescription() {
            const measure = this.props.measures.find(m => m.fieldName === this.props.measure);
            return measure ? measure.description : this.props.fields[this.props.measure].string;
        }

        //---------------------------------------------------------------------
        // Private
        //---------------------------------------------------------------------

        /**
         * This function aims to remove a suitable number of lines from the
         * tooltip in order to make it reasonably visible. A message indicating
         * the number of lines is added if necessary.
         * @private
         * @param {Number} maxTooltipHeight this the max height in pixels of the tooltip
         */
        _adjustTooltipHeight(maxTooltipHeight) {
            const sizeOneLine = this.tooltip.querySelector("tbody tr").clientHeight;
            const tbodySize = this.tooltip.querySelector("tbody").clientHeight;
            const toKeep = Math.max(0, Math.floor(
                (maxTooltipHeight - (this.tooltip.clientHeight - tbodySize)
                ) / sizeOneLine) - 1);
            const lines = this.tooltip.querySelectorAll("tbody tr");
            const toRemove = lines.length - toKeep;
            if (toRemove > 0) {
                for (let index = toKeep; index < lines.length; ++index) {
                    lines[index].remove();
                }
                const tr = document.createElement("tr");
                const td = document.createElement("td");
                tr.classList.add("o_show_more");
                td.innerHTML = this.env._t("...");
                tr.appendChild(td);
                this.tooltip.querySelector("tbody").appendChild(tr);
            }
        }

        /**
         * Creates a bar chart config.
         * @private
         */
        _createBarChartConfig() {
            // prepare data
            const data = this._prepareData(this.processedDataPoints);

            for (let index = 0; index < data.datasets.length; ++index) {
                const dataset = data.datasets[index];
                // used when stacked
                if (this.props.stacked) {
                    dataset.stack = this.props.origins[dataset.originIndex];
                }
                // set dataset color
                dataset.backgroundColor = getColor(index);
            }

            // prepare options
            const options = this._prepareOptions(data.datasets.length);

            // create bar chart config
            return { data, options, type: "bar" };
        }

        /**
         * Returns the graph configuration object.
         * @private
         * @returns {Object}
         */
        _createConfig() {
            if (this.noContentHelperData) {
                return {};
            }
            if (this.props.comparisonFieldIndex === 0) {
                this.dateClasses = this._getDateClasses(this.processedDataPoints);
            }
            switch (this.props.mode) {
                case "bar": return this._createBarChartConfig();
                case "line": return this._createLineChartConfig();
                case "pie": return this._createPieChartConfig();
            }
        }

        /**
         * Creates a line chart config.
         * @private
         */
        _createLineChartConfig() {
            // prepare data
            const data = this._prepareData(this.processedDataPoints);
            for (let index = 0; index < data.datasets.length; ++index) {
                const dataset = data.datasets[index];
                if (
                    this.props.processedGroupBy.length <= 1 &&
                    this.props.origins.length > 1
                ) {
                    if (dataset.originIndex === 0) {
                        dataset.fill = "origin";
                        dataset.backgroundColor = hexToRGBA(COLORS[0], 0.4);
                        dataset.borderColor = hexToRGBA(COLORS[0], 1);
                    } else if (dataset.originIndex === 1) {
                        dataset.borderColor = hexToRGBA(COLORS[1], 1);
                    } else {
                        dataset.borderColor = getColor(index);
                    }
                } else {
                    dataset.borderColor = getColor(index);
                }
                if (data.labels.length === 1) {
                    // shift of the real value to right. This is done to
                    // center the points in the chart. See data.labels below in
                    // Chart parameters
                    dataset.data.unshift(undefined);
                }
                dataset.pointBackgroundColor = dataset.borderColor;
                dataset.pointBorderColor = "rgba(0,0,0,0.2)";
            }
            if (data.datasets.length === 1 && data.datasets[0].originIndex === 0) {
                const dataset = data.datasets[0];
                dataset.fill = "origin";
                dataset.backgroundColor = hexToRGBA(COLORS[0], 0.4);
            }

            // center the points in the chart (without that code they are put
            // on the left and the graph seems empty)
            data.labels = data.labels.length > 1 ?
                data.labels :
                [this.fakeDataLabel, ...data.labels, this.fakeDataLabel];

            // prepare options
            const options = this._prepareOptions(data.datasets.length);

            // create line chart config
            return { data, options, type: "line" };
        }

        /**
         * Creates a pie chart config.
         * @private
         */
        _createPieChartConfig() {
            // prepare data
            let data = {};
            const allZero = this.processedDataPoints.every(
                datapt => datapt.value === 0
            );
            if (allZero) {
                // add fake data to display a pie chart with a grey zone associated
                // with every origin
                data.labels = [this.noDataLabel];
                data.datasets = this.props.origins.map(origin => {
                    return {
                        label: origin,
                        data: [1],
                        backgroundColor: [DEFAULT_BG],
                    };
                });
            } else {
                data = this._prepareData(this.processedDataPoints);
                // give same color to same groups from different origins
                const colors = data.labels.map((_, index) => getColor(index));
                for (const dataset of data.datasets) {
                    dataset.backgroundColor = colors;
                    dataset.borderColor = "rgba(255,255,255,0.6)";
                }
                // make sure there is a zone associated with every origin
                const representedOriginIndexes = data.datasets.map(
                    dataset => dataset.originIndex
                );
                let addNoDataToLegend = false;
                const fakeData = new Array(data.labels.length).concat([1]);

                for (let index = 0; index < this.props.origins.length; ++index) {
                    const origin = this.props.origins[index];
                    if (!representedOriginIndexes.includes(index)) {
                        data.datasets.splice(index, 0, {
                            label: origin,
                            data: fakeData,
                            backgroundColor: [...colors, DEFAULT_BG],
                        });
                        addNoDataToLegend = true;
                    }
                }
                if (addNoDataToLegend) {
                    data.labels.push(this.noDataLabel);
                }
            }

            // prepare options
            const options = this._prepareOptions(data.datasets.length);

            // create pie chart config
            return { data, options, type: "pie" };
        }

        /**
         * Creates a custom HTML tooltip.
         * @private
         * @param {Object} tooltipModel see chartjs documentation
         */
        _customTooltip(tooltipModel) {
            this.el.style.cursor = "";
            this._removeTooltips();
            if (tooltipModel.opacity === 0 || tooltipModel.dataPoints.length === 0) {
                return;
            }
            if (this._isRedirectionEnabled()) {
                this.el.style.cursor = "pointer";
            }

            const chartAreaTop = this.chart.chartArea.top;
            const rendererTop = this.el.getBoundingClientRect().top;

            const innerHTML = this.env.qweb.renderToString("web.GraphRenderer.CustomTooltip", {
                maxWidth: getMaxWidth(this.chart.chartArea),
                measure: this.measureDescription,
                mode: this.props.mode,
                tooltipItems: this._getTooltipItems(tooltipModel),
            });
            const template = Object.assign(document.createElement("template"), { innerHTML });
            this.tooltip = template.content.firstChild;

            this.containerRef.el.prepend(this.tooltip);

            let top;
            const tooltipHeight = this.tooltip.clientHeight;
            const minTopAllowed = Math.floor(chartAreaTop);
            const maxTopAllowed = Math.floor(window.innerHeight - (rendererTop + tooltipHeight)) - 2;
            const y = Math.floor(tooltipModel.y);

            if (minTopAllowed <= maxTopAllowed) {
                // Here we know that the full tooltip can fit in the screen.
                // We put it in the position where Chart.js would put it
                // if two conditions are respected:
                //  1: the tooltip is not cut (because we know it is possible to not cut it)
                //  2: the tooltip does not hide the legend.
                // If it is not possible to use the Chart.js proposition (y)
                // we use the best approximated value.
                if (y <= maxTopAllowed) {
                    if (y >= minTopAllowed) {
                        top = y;
                    } else {
                        top = minTopAllowed;
                    }
                } else {
                    top = maxTopAllowed;
                }
            } else {
                // Here we know that we cannot satisfy condition 1 above,
                // so we position the tooltip at the minimal position and
                // cut it the minimum possible.
                top = minTopAllowed;
                const maxTooltipHeight = window.innerHeight - (rendererTop + chartAreaTop) - 2;
                this._adjustTooltipHeight(maxTooltipHeight);
            }

            this._fixTooltipLeftPosition(this.tooltip, tooltipModel.x);
            this.tooltip.style.top = Math.floor(top) + "px";
        }

        /**
         * Filters out some dataPoints because they would lead to bad graphics.
         * The filtering is done with respect to the graph view mode.
         * Note that the method does not alter this.state.dataPoints, since we
         * want to be able to change of mode without fetching data again:
         * we simply present the same data in a different way.
         * Note: this should be moved to the model at some point.
         * @private
         * @param {Object} props
         * @returns {Object[]}
         */
        _filterDataPoints(props) {
            let dataPoints = [];
            if (props.mode === "line") {
                let counts = 0;
                for (const dataPoint of props.dataPoints) {
                    if (dataPoint.labels[0] !== this.env._t("Undefined")) {
                        dataPoints.push(dataPoint);
                    }
                    counts += dataPoint.count;
                }
                // data points with zero count might have been created on purpose
                // we only remove them if there are no data point with positive count
                if (counts === 0) {
                    dataPoints = [];
                }
            } else {
                dataPoints = props.dataPoints.filter(
                    dataPoint => dataPoint.count > 0
                );
            }
            return dataPoints;
        }

        /**
         * Sets best left position of a tooltip approaching the proposal x.
         * @private
         * @param {DOMElement} tooltip
         * @param {number} x, left offset proposed
         */
        _fixTooltipLeftPosition(tooltip, x) {
            let left;
            const tooltipWidth = tooltip.clientWidth;
            const minLeftAllowed = Math.floor(this.chart.chartArea.left + 2);
            const maxLeftAllowed = Math.floor(this.chart.chartArea.right - tooltipWidth - 2);
            x = Math.floor(x);
            if (x <= maxLeftAllowed) {
                if (x >= minLeftAllowed) {
                    left = x;
                } else {
                    left = minLeftAllowed;
                }
            } else {
                left = maxLeftAllowed;
            }
            tooltip.style.left = left + "px";
        }

        /**
         * Used to format correctly the values in tooltips and yAxes.
         * @private
         * @param {number} value
         * @returns {string} The value formatted using fieldUtils.format.float
         */
        _formatValue(value) {
            const formatter = fieldUtils.format.float;
            const measure = this.props.fields[this.props.measure];
            const formatedValue = formatter(value, measure, FORMAT_OPTIONS);
            return formatedValue;
        }

        /**
         * Determines the initial section of the labels array over which
         * a dataset has to be completed. The section only depends on the
         * datasets origins.
         * @private
         * @param {number} originIndex
         * @param {number} defaultLength
         * @returns {number}
         */
        _getDatasetDataLength(originIndex, defaultLength) {
            if (this.props.mode !== "pie" && this.props.comparisonFieldIndex === 0) {
                return this.dateClasses.dateSets[originIndex].length;
            }
            return defaultLength;
        }

        /**
         * Determines the dataset to which the data point belongs.
         * @private
         * @param {Object} dataPoint
         * @returns {string}
         */
        _getDatasetLabel({ labels, originIndex }) {
            if (this.props.mode === "pie") {
                return this.props.origins[originIndex];
            }
            // ([origin] + second to last groupBys) or measure
            let datasetLabel = labels.slice(1).join("/");
            if (this.props.origins.length > 1) {
                datasetLabel = this.props.origins[originIndex] + (
                    datasetLabel ? ("/" + datasetLabel) : ""
                );
            }
            return datasetLabel || this.measureDescription;
        }

        /**
         * Returns a DateClasses instance used to manage equivalence of dates.
         * @private
         * @param {Object[]} dataPoints
         * @returns {DateClasses}
         */
        _getDateClasses(dataPoints) {
            const dateSets = this.props.origins.map(() => []);
            for (const { labels, originIndex } of dataPoints) {
                dateSets[originIndex].push(labels[this.props.comparisonFieldIndex]);
            }
            return new DateClasses(dateSets.map(dateSet => [...new Set(dateSet)]));
        }

        /**
         * Returns an object used to style chart elements independently from
         * the datasets.
         * @private
         * @returns {Object}
         */
        _getElementOptions() {
            const elementOptions = {};
            if (this.props.mode === "bar") {
                elementOptions.rectangle = { borderWidth: 1 };
            } else if (this.props.mode === "line") {
                elementOptions.line = {
                    tension: 0,
                    fill: false,
                };
            }
            return elementOptions;
        }

        /**
         * Gets the label over which the data point is.
         * @private
         * @param {Object} dataPoint
         * @returns {Array}
         */
        _getLabel({ labels, originIndex }) {
            const index = this.props.comparisonFieldIndex;
            if (this.props.mode !== "pie") {
                if (index === 0) {
                    return [this.dateClasses.dateClass(originIndex, labels[index])];
                } else {
                    return labels.slice(0, 1);
                }
            } else if (index === 0) {
                return [
                    this.dateClasses.dateClass(originIndex, labels[index]),
                    ...labels.slice(index + 1)
                ];
            } else {
                return labels;
            }
        }

        /**
         * Returns the options used to generate the chart legend.
         * @private
         * @param {number} datasetsCount
         * @returns {Object}
         */
        _getLegendOptions(datasetsCount) {
            const legendOptions = {
                display: datasetsCount <= MAX_LEGEND_LENGTH,
                position: "top",
                onHover: this._onlegendHover.bind(this),
                onLeave: this._onLegendLeave.bind(this),
            };
            if (this.props.mode === "line") {
                legendOptions.onClick = this._onLegendClick.bind(this);
            }
            if (this.props.mode !== "pie") {
                let referenceColor;
                if (this.props.mode === "bar") {
                    referenceColor = "backgroundColor";
                } else {
                    referenceColor = "borderColor";
                }
                legendOptions.labels = {
                    generateLabels: chart => {
                        const { data } = chart;
                        const labels = data.datasets.map((dataset, index) => {
                            return {
                                text: shortenLabel(dataset.label),
                                fullText: dataset.label,
                                fillStyle: dataset[referenceColor],
                                hidden: !chart.isDatasetVisible(index),
                                lineCap: dataset.borderCapStyle,
                                lineDash: dataset.borderDash,
                                lineDashOffset: dataset.borderDashOffset,
                                lineJoin: dataset.borderJoinStyle,
                                lineWidth: dataset.borderWidth,
                                strokeStyle: dataset[referenceColor],
                                pointStyle: dataset.pointStyle,
                                datasetIndex: index,
                            };
                        });
                        return labels;
                    },
                };
            } else {
                const { comparisonFieldIndex } = this.props;
                legendOptions.labels = {
                    generateLabels: chart => {
                        const { data } = chart;
                        const metaData = data.datasets.map(
                            (_, index) => chart.getDatasetMeta(index).data
                        );
                        const labels = data.labels.map((label, index) => {
                            const hidden = metaData.some(
                                data => data[index] && data[index].hidden
                            );
                            const fullText = this._relabelling(label, comparisonFieldIndex);
                            const text = shortenLabel(fullText);
                            const fillStyle = label === this.noDataLabel ?
                                DEFAULT_BG :
                                getColor(index);
                            return { text, fullText, fillStyle, hidden, index };
                        });
                        return labels;
                    },
                };
            }
            return legendOptions;
        }

        /**
         * Determines whether the data are good, and displays an error message
         * if this is not the case.
         * @private
         * @returns {Object | null}
         */
        _getNoContentHelper() {
            if (this.props.mode === "pie") {
                const dataPoints = this.processedDataPoints;
                const someNegative = dataPoints.some(dataPt => dataPt.value < 0);
                const somePositive = dataPoints.some(dataPt => dataPt.value > 0);
                if (someNegative && somePositive) {
                    return {
                        title: this.env._t("Invalid data"),
                        description: [
                            this.env._t("Pie chart cannot mix positive and negative numbers. "),
                            this.env._t("Try to change your domain to only display positive results")
                        ].join("")
                    };
                }
            }
            return null;
        }

        /**
         * Returns the options used to generate the chart axes.
         * @private
         * @returns {Object}
         */
        _getScaleOptions() {
            if (this.props.mode === "pie") {
                return {};
            }
            const { comparisonFieldIndex } = this.props;
            const xAxes = [{
                type: "category",
                scaleLabel: {
                    display: this.props.processedGroupBy.length && !this.props.isEmbedded,
                    labelString: this.props.processedGroupBy.length ?
                        this.props.fields[this.props.processedGroupBy[0].split(":")[0]].string :
                        "",
                },
                ticks: { callback: label => this._relabelling(label, comparisonFieldIndex) },
            }];
            const yAxes = [{
                type: "linear",
                scaleLabel: {
                    display: !this.props.isEmbedded,
                    labelString: this.measureDescription,
                },
                ticks: {
                    callback: value => this._formatValue(value),
                    suggestedMax: 0,
                    suggestedMin: 0,
                },
            }];
            return { xAxes, yAxes };
        }

        /**
         * Extracts the important information from a tooltipItem generated by
         * Charts.js (a tooltip item corresponds to a line (different from
         * measure name) of a tooltip).
         * @private
         * @param {Object} item
         * @param {Object} data
         * @returns {Object}
         */
        _getTooltipItemContent(item, data) {
            const { comparisonFieldIndex } = this.props;
            const dataset = data.datasets[item.datasetIndex];
            const id = item.index;
            let label = data.labels[item.index];
            let value;
            let boxColor;
            let percentage;
            if (this.props.mode === "pie") {
                if (label === this.noDataLabel) {
                    value = this._formatValue(0);
                } else {
                    value = this._formatValue(dataset.data[item.index]);
                    const totalData = dataset.data.reduce((a, b) => a + b, 0);
                    percentage = totalData && ((dataset.data[item.index] * 100) / totalData).toFixed(2);
                }
                label = this._relabelling(label, comparisonFieldIndex, dataset.originIndex);
                if (this.props.origins.length > 1) {
                    label = `${dataset.label}/${label}`;
                }
                boxColor = dataset.backgroundColor[item.index];
            } else {
                label = this._relabelling(label, comparisonFieldIndex, dataset.originIndex);
                if (
                    this.props.processedGroupBy.length > 1 ||
                    this.props.origins.length > 1
                ) {
                    label = `${label}/${dataset.label}`;
                }
                value = this._formatValue(item.yLabel);
                boxColor = this.props.mode === "bar" ?
                    dataset.backgroundColor :
                    dataset.borderColor;
            }
            return { id, label, value, boxColor, percentage };
        }

        /**
         * This function extracts the information from the data points in
         * tooltipModel.dataPoints (corresponding to datapoints over a given
         * label determined by the mouse position) that will be displayed in a
         * custom tooltip.
         * @private
         * @param {Object} tooltipModel see chartjs documentation
         * @return {Object[]}
         */
        _getTooltipItems(tooltipModel) {
            const { data } = this.chart.config;
            const sortedDataPoints = sortBy(tooltipModel.dataPoints, "yLabel", "desc");
            return sortedDataPoints.map(
                item => this._getTooltipItemContent(item, data)
            );
        }

        /**
         * Returns the options used to generate chart tooltips.
         * @private
         * @returns {Object}
         */
        _getTooltipOptions() {
            const tooltipOptions = {
                // disable Chart.js tooltips
                enabled: false,
                custom: this._customTooltip.bind(this),
            };
            if (this.props.mode === "line") {
                tooltipOptions.mode = "index";
                tooltipOptions.intersect = false;
            }
            return tooltipOptions;
        }

        /**
         * Returns true iff the current graph can be clicked on to redirect to
         * the list of records.
         * @private
         * @returns {boolean}
         */
        _isRedirectionEnabled() {
            return !this.props.disableLinking && this.props.mode !== "line";
        }

        /**
         * Separates dataPoints coming from the read_group(s) into different
         * datasets. This function returns the parameters data and labels used
         * to produce the charts.
         * @param {Object[]} dataPoints
         * @returns {Object}
         */
        _prepareData(dataPoints) {
            const labelMap = {};
            const labels = [];
            for (const dataPt of dataPoints) {
                const label = this._getLabel(dataPt);
                const labelKey = `${dataPt.resId}:${JSON.stringify(label)}`;
                const index = labelMap[labelKey];
                if (index === undefined) {
                    labelMap[labelKey] = dataPt.labelIndex = labels.length;
                    labels.push(label);
                } else {
                    dataPt.labelIndex = index;
                }
            }

            // dataPoints --> datasets
            const datasetsTmp = {};
            for (const dp of dataPoints) {
                const datasetLabel = this._getDatasetLabel(dp);
                if (!(datasetLabel in datasetsTmp)) {
                    const dataLength = this._getDatasetDataLength(dp.originIndex, labels.length);
                    datasetsTmp[datasetLabel] = {
                        data: new Array(dataLength).fill(0),
                        domain: new Array(dataLength).fill([]),
                        label: datasetLabel,
                        originIndex: dp.originIndex,
                    };
                }
                const labelIndex = dp.labelIndex;
                datasetsTmp[datasetLabel].data[labelIndex] = dp.value;
                datasetsTmp[datasetLabel].domain[labelIndex] = dp.domain;
            }
            // sort by origin
            const datasets = sortBy(Object.values(datasetsTmp), "originIndex");
            return { datasets, labels };
        }

        /**
         * Prepares options for the chart according to the current mode
         * (= chart type). This function returns the parameter options used to
         * instantiate the chart.
         * @private
         * @param {number} datasetsCount
         * @returns {Object} the chart options used for the current mode
         */
        _prepareOptions(datasetsCount) {
            const options = {
                maintainAspectRatio: false,
                scales: this._getScaleOptions(),
                legend: this._getLegendOptions(datasetsCount),
                tooltips: this._getTooltipOptions(),
                elements: this._getElementOptions(),
            };
            if (this._isRedirectionEnabled()) {
                options.onClick = ev => this._onGraphClicked(ev);
            }
            return options;
        }

        /**
         * Computes various information from the given props object.
         * @param {Object} props
         */
        _processProps(props) {
            const filteredDataPoints = this._filterDataPoints(props);
            this.processedDataPoints = this._sortDataPoints(filteredDataPoints, props);
            this.noContentHelperData = this._getNoContentHelper(props.mode);
        }

        /**
         * Determines how to relabel a label according to a given origin. The
         * idea is that the getLabel function is in general not invertible but
         * it is when restricted to the set of dataPoints coming from a same
         * origin.
         * @private
         * @param {Array} label
         * @param {number} index
         * @param {Array} [originIndex]
         * @returns {string}
         */
        _relabelling(label, index, originIndex) {
            if (label === this.noDataLabel || label === this.fakeDataLabel) {
                return label[0];
            }
            if (this.props.mode !== "pie" && index === 0) {
                // here label is an array of length 1 and contains a number
                return this.dateClasses.representative(label, originIndex) || "";
            } else if (this.props.mode === "pie" && index === 0) {
                // here label is an array of length at least one containing string or numbers
                const labelCopy = label.slice();
                let newLabel;
                if (originIndex === undefined) {
                    newLabel = this.dateClasses.dateClassMembers(label[index]);
                } else {
                    newLabel = this.dateClasses.representative(label[index], originIndex);
                }
                labelCopy.splice(index, 1, newLabel);
                return labelCopy.join("/");
            }
            // here label is an array containing strings or numbers.
            return label.join("/") || this.env._t("Total");
        }

        /**
         * Removes all existing tooltips.
         * @private
         */
        _removeTooltips() {
            if (this.tooltip) {
                this.tooltip.remove();
                this.tooltip = null;
            }
            if (this.legendTooltip) {
                this.legendTooltip.remove();
                this.legendTooltip = null;
            }
        }

        /**
         * Instantiates a Chart (Chart.js lib) to render the graph according to
         * the current config.
         * @private
         */
        _renderChart() {
            if (this.noContentHelperData) {
                return;
            }
            if (this.chart) {
                this.chart.destroy();
            }
            const config = this._createConfig();
            const canvasContext = this.canvasRef.el.getContext("2d");
            this.chart = new Chart(canvasContext, config);
            // To perform its animations, ChartJS will perform each animation
            // step in the next animation frame. The initial rendering itself
            // is delayed for consistency. We can avoid this by manually
            // advancing the animation service.
            Chart.animationService.advance();
        }

        /**
         * Sorts datapoints according to the current order (ASC or DESC).
         * Note: this should be moved to the model at some point.
         * @private
         * @param {Object[]} dataPoints
         * @param {Object} props
         * @returns {Object[]} sorted dataPoints if orderby set on state
         */
        _sortDataPoints(dataPoints, props) {
            if (
                props.domains.length === 1 &&
                props.orderBy &&
                props.mode !== "pie" &&
                props.processedGroupBy.length
            ) {
                // group data by their x-axis value, and then sort datapoints
                // based on the sum of values by group in ascending/descending order
                const [groupByFieldName] = props.processedGroupBy[0].split(":");
                const { type } = props.fields[groupByFieldName];
                const groupedDataPoints = {};
                for (const dataPt of dataPoints) {
                    const key = type === "many2one" ? dataPt.resId : dataPt.labels[0];
                    if (!groupedDataPoints[key]) {
                        groupedDataPoints[key] = [];
                    }
                    groupedDataPoints[key].push(dataPt);
                }
                const groupTotal = group => group.reduce((sum, { value }) => sum + value, 0);
                dataPoints = sortBy(
                    Object.values(groupedDataPoints),
                    groupTotal,
                    props.orderBy
                ).flat();
            }
            return dataPoints;
        }

        //---------------------------------------------------------------------
        // Handlers
        //---------------------------------------------------------------------

        /**
         * @private
         * @param {MouseEvent} ev
         */
        _onGraphClicked(ev) {
            const [activeElement] = this.chart.getElementAtEvent(ev);
            if (!activeElement) {
                return;
            }
            const { _datasetIndex, _index } = activeElement;
            const { domain } = this.chart.data.datasets[_datasetIndex];
            if (domain) {
                this.trigger("open_view", { domain: domain[_index] });
            }
        }

        /**
         * Overrides the default legend 'onClick' behaviour. This is done to
         * remove all existing tooltips right before updating the chart.
         * @private
         * @param {MouseEvent} ev
         * @param {Object} legendItem
         */
        _onLegendClick(ev, legendItem) {
            this._removeTooltips();
            // Default 'onClick' fallback. See web/static/lib/Chart/Chart.js#15138
            const index = legendItem.datasetIndex;
            const meta = this.chart.getDatasetMeta(index);
            meta.hidden = meta.hidden === null ? !this.chart.data.datasets[index].hidden : null;
            this.chart.update();
        }

        /**
         * If the text of a legend item has been shortened and the user mouse
         * hovers that item (actually the event type is mousemove), a tooltip
         * with the item full text is displayed.
         * @private
         * @param {MouseEvent} ev
         * @param {Object} legendItem
         */
        _onlegendHover(ev, legendItem) {
            this.canvasRef.el.style.cursor = "pointer";
            /**
             * The string legendItem.text is an initial segment of legendItem.fullText.
             * If the two coincide, no need to generate a tooltip. If a tooltip
             * for the legend already exists, it is already good and doesn't
             * need to be recreated.
             */
            if (legendItem.text === legendItem.fullText || this.legendTooltip) {
                return;
            }

            const rendererTop = this.el.getBoundingClientRect().top;

            this.legendTooltip = Object.assign(document.createElement("div"), {
                className: "o_tooltip_legend",
                innerText: legendItem.fullText,
            });
            this.legendTooltip.style.top = (ev.clientY - rendererTop) + "px";
            this.legendTooltip.style.maxWidth = getMaxWidth(this.chart.chartArea);

            this.containerRef.el.appendChild(this.legendTooltip);

            this._fixTooltipLeftPosition(this.legendTooltip, ev.clientX);
        }

        /**
         * If there's a legend tooltip and the user mouse out of the
         * corresponding legend item, the tooltip is removed.
         * @private
         */
        _onLegendLeave() {
            this.canvasRef.el.style.cursor = "";
            if (this.legendTooltip) {
                this.legendTooltip.remove();
                this.legendTooltip = null;
            }
        }
    }

    GraphRenderer.template = "web.Legacy.GraphRenderer";
    GraphRenderer.props = {
        arch: {
            type: Object,
            shape: {
                children: { type: Array, element: Object },
                attrs: Object,
                tag: { validate: t => t === "graph" },
            },
        },
        comparisonFieldIndex: Number,
        context: Object,
        dataPoints: { type: Array, element: Object },
        disableLinking: Boolean,
        domain: [Array, String],
        domains: { type: Array, element: [Array, String] },
        fields: Object,
        groupBy: { type: Array, element: String },
        isEmbedded: Boolean,
        isSample: { type: Boolean, optional: 1 },
        measure: String,
        measures: { type: Array, element: Object },
        mode: { validate: m => ["bar", "line", "pie"].includes(m) },
        origins: { type: Array, element: String },
        processedGroupBy: { type: Array, element: String },
        stacked: Boolean,
        timeRanges: Object,
        noContentHelp: { type: String, optional: 1 },
        orderBy: { type: [String, Boolean], optional: 1 },
        title: { type: String, optional: 1 },
        withSearchPanel: { type: Boolean, optional: 1 },
    };

    return GraphRenderer;

});
