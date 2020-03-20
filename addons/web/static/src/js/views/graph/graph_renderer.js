odoo.define('web.GraphRenderer', function (require) {
    'use strict';

    const OwlAbstractRenderer = require('web.AbstractRendererOwl');
    const dataComparisonUtils = require('web.dataComparisonUtils');
    const config = require('web.config');
    const DateClasses = dataComparisonUtils.DateClasses;
    const fieldUtils = require('web.field_utils');
    const core = require('web.core');
    const _t = core._t;
    const qweb = core.qweb;

    const NO_DATA = [_t('No data')];
    NO_DATA.isNoData = true;
    const CHART_TYPES = ['pie', 'bar', 'line'];

    const COLORS = ["#1f77b4", "#ff7f0e", "#aec7e8", "#ffbb78", "#2ca02c", "#98df8a", "#d62728",
        "#ff9896", "#9467bd", "#c5b0d5", "#8c564b", "#c49c94", "#e377c2", "#f7b6d2",
        "#7f7f7f", "#c7c7c7", "#bcbd22", "#dbdb8d", "#17becf", "#9edae5"];
    const COLOR_NB = COLORS.length;

    // used to format values in tooltips and yAxes.
    const FORMAT_OPTIONS = {
        // allow to decide if utils.human_number should be used
        humanReadable: value => {
            return Math.abs(value) >= 1000;
        },
        // with the choices below, 1236 is represented by 1.24k
        minDigits: 1,
        decimals: 2,
        // avoid comma separators for thousands in numbers when human_number is used
        formatterCallback: str => {
            return str;
        },
    };

    // hide top legend when too many items for device size
    const MAX_LEGEND_LENGTH = 4 * (Math.max(1, config.device.size_class));

    const {useState, useRef } = owl.hooks;
    class GraphOwlRenderer extends OwlAbstractRenderer {

        constructor() {
            super(...arguments);
            this.noContentHelperData = {show: false, title: "", description: ""};
            this.canvasRef = useRef("canvas");

            this.filteredDataPoints = this._filterDataPoints(this.props);
            this._setNoContentHelper(this.props);
        }

        mounted() {
            this._renderChart();
        }

        async willUpdateProps(nextProps) {
            this.filteredDataPoints = this._filterDataPoints(nextProps);
            this._setNoContentHelper(nextProps);
        }

        patched() {
            this._renderChart();
        }

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * This function aims to remove a suitable number of lines from the tooltip in order to make it reasonably visible.
         * A message indicating the number of lines is added if necessary.
         *
         * @private
         * @param {Number} maxTooltipHeight this the max height in pixels of the tooltip
         */
        _adjustTooltipHeight(maxTooltipHeight) {
            const sizeOneLine = this.tooltip.querySelector('tbody tr').clientHeight;
            const tbodySize = this.tooltip.querySelector('tbody').clientHeight;
            const toKeep = Math.floor((maxTooltipHeight - (this.tooltip.clientHeight - tbodySize)) / sizeOneLine) - 1;
            const lines = this.tooltip.querySelectorAll('tbody tr');
            const toRemove = lines.length - toKeep;
            if (toRemove > 0) {
                for (let i = toKeep; i < lines.length; ++i) {
                    lines[i].remove();
                }

                const tr = document.createElement('tr');
                const td = document.createElement('td');
                tr.classList.add('o_show_more');
                td.innerHTML = _t("...");
                tr.appendChild(td);
                this.tooltip.querySelector('tbody').appendChild(tr);
            }
        }

        /**
         * This function creates a custom HTML tooltip.
         *
         * @private
         * @param {Object} tooltipModel see chartjs documentation
         */
        _customTooltip(tooltipModel) {
            this.el.style.cursor = 'default';
            if (this.tooltip) {
                this.tooltip.remove();
            }

            if (tooltipModel.opacity === 0) {
                return;
            }
            if (tooltipModel.dataPoints.length === 0) {
                return;
            }

            if (this._isRedirectionEnabled()) {
                this.el.style.cursor = 'pointer';
            }

            const chartArea = this.chart.chartArea;
            const chartAreaLeft = chartArea.left;
            const chartAreaRight = chartArea.right;
            const chartAreaTop = chartArea.top;
            const rendererTop = this.el.getBoundingClientRect().top;

            const maxTooltipLabelWidth = Math.floor((chartAreaRight - chartAreaLeft) / 1.68) + 'px';
            const tooltipItems = this._getTooltipItems(tooltipModel);

            const template = document.createElement('template');
            const tooltipHtml = qweb.render('GraphView.CustomTooltip', {
                measure: this.props.fields[this.props.measure].string,
                tooltipItems: tooltipItems,
                maxWidth: maxTooltipLabelWidth,
            });
            template.innerHTML = tooltipHtml;
            this.tooltip = template.content.firstChild;

            const container = this.el.querySelector('.o_graph_canvas_container');
            container.appendChild(this.tooltip);

            let top;
            const tooltipHeight = this.tooltip.clientHeight;
            const minTopAllowed = Math.floor(chartAreaTop);
            const maxTopAllowed = Math.floor(window.innerHeight - rendererTop - tooltipHeight) - 2;
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
                const maxTooltipHeight = window.innerHeight - (rendererTop + chartAreaTop) -2;
                this._adjustTooltipHeight(maxTooltipHeight);
            }

            this._fixTooltipLeftPosition(this.tooltip, tooltipModel.x);
            this.tooltip.style.top = Math.floor(top) + 'px';
        }

        /**
         * Filter out some dataPoints because they would lead to bad graphics.
         * The filtering is done with respect to the graph view mode.
         * Note that the method does not alter this.state.dataPoints, since we
         * want to be able to change of mode without fetching data again:
         * we simply present the same data in a different way.
         *
         * @private
         * @param {Object} props
         * @returns {Object[]}
         */
        _filterDataPoints(props) {
            let dataPoints = [];
            if (['bar', 'pie'].includes(props.mode)) {
                dataPoints = props.dataPoints.filter(dataPt => {
                    return dataPt.count > 0;
                });
            } else if (props.mode === 'line') {
                var counts = 0;
                for (const dataPt of props.dataPoints) {
                    if (dataPt.labels[0] !== _t("Undefined")) {
                        dataPoints.push(dataPt);
                    }
                    counts += dataPt.count;
                }
                // data points with zero count might have been created on purpose
                // we only remove them if there are no data point with positive count
                if (counts === 0) {
                    dataPoints = [];
                }
            }
            return dataPoints;
        }

        /**
         * Used to format correctly the values in tooltips and yAxes
         *
         * @private
         * @param {number} value
         * @returns {string} The value formatted using fieldUtils.format.float
         */
        _formatValue(value) {
            const measureField = this.props.fields[this.props.measure];
            const formatter = fieldUtils.format.float;
            const formatedValue = formatter(value, measureField, FORMAT_OPTIONS);
            return formatedValue;
        }

        /**
         * Sets best left position of a tooltip approaching the proposal x
         *
         * @private
         * @param {DOMElement} tooltip
         * @param {number} x, left offset proposed
         */
        _fixTooltipLeftPosition(tooltip, x) {
            let left;
            const tooltipWidth = tooltip.clientWidth;
            const minLeftAllowed = Math.floor(this.chart.chartArea.left + 2);
            const maxLeftAllowed = Math.floor(this.chart.chartArea.right - tooltipWidth -2);
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
            tooltip.style.left = left + 'px';
        }

        /**
         * Used any time we need a new color in our charts.
         *
         * @private
         * @param {number} index
         * @returns {string} a color in HEX format
         */
        _getColor(index) {
            return COLORS[index % COLOR_NB];
        }

        /**
         * Determines the initial section of the labels array
         * over a dataset has to be completed. The section only depends
         * on the datasets origins.
         *
         * @private
         * @param {number} originIndex
         * @param {number} defaultLength
         * @returns {number}
         */
        _getDatasetDataLength(originIndex, defaultLength) {
            if (['bar', 'line'].includes(this.props.mode) && this.props.comparisonFieldIndex === 0) {
                return this.dateClasses.dateSets[originIndex].length;
            }
            return defaultLength;
        }

        /**
         * Determines to which dataset belong the data point
         *
         * @private
         * @param {Object} dataPt
         * @returns {string}
         */
        _getDatasetLabel(dataPt) {
            if (['bar', 'line'].includes(this.props.mode)) {
                // ([origin] + second to last groupBys) or measure
                let datasetLabel = dataPt.labels.slice(1).join("/");
                if (this.props.origins.length > 1) {
                    datasetLabel = this.props.origins[dataPt.originIndex] +
                        (datasetLabel ? ('/' + datasetLabel) : '');
                }
                datasetLabel = datasetLabel || this.props.fields[this.props.measure].string;
                return datasetLabel;
            }
            return this.props.origins[dataPt.originIndex];
        }

        /**
         * Returns a DateClasses instance used to manage equivalence of dates.
         *
         * @private
         * @param {Object[]} dataPoints
         * @returns {DateClasses}
         */
        _getDateClasses(dataPoints) {
            var dateSets = this.props.origins.map(() => {
                return [];
            });
            for (const dataPt of dataPoints) {
                dateSets[dataPt.originIndex].push(dataPt.labels[this.props.comparisonFieldIndex]);
            }
            dateSets = dateSets.map(dateSet => {
                return [...(new Set(dateSet))];
            });
            return new DateClasses(dateSets);
        }

        /**
         * Returns an object used to style chart elements independently from the datasets.
         *
         * @private
         * @returns {Object}
         */
        _getElementOptions() {
            const elementOptions = {};
            if (this.props.mode === 'bar') {
                elementOptions.rectangle = {borderWidth: 1};
            } else if (this.props.mode === 'line') {
                elementOptions.line = {
                    tension: 0,
                    fill: false,
                };
            }
            return elementOptions;
        }

        /**
         * Determines over which label is the data point
         *
         * @private
         * @param {Object} dataPt
         * @returns {Array}
         */
        _getLabel(dataPt) {
            const i = this.props.comparisonFieldIndex;
            if (['bar', 'line'].includes(this.props.mode)) {
                if (i === 0) {
                    return [this.dateClasses.dateClass(dataPt.originIndex, dataPt.labels[i])];
                } else {
                    return dataPt.labels.slice(0, 1);
                }
            } else if (i === 0) {
                return Array.prototype.concat.apply([], [
                            this.dateClasses.dateClass(dataPt.originIndex, dataPt.labels[i]),
                            dataPt.labels.slice(i+1)
                        ]);
            } else {
                return dataPt.labels;
            }
        }

        /**
         * Returns the options used to generate the chart legend.
         *
         * @private
         * @param {Number} datasetsCount
         * @returns {Object}
         */
        _getLegendOptions(datasetsCount) {
            const legendOptions = {
                display: datasetsCount <= MAX_LEGEND_LENGTH,
                position: 'top',
                onHover: this._onlegendTooltipHover.bind(this),
                onLeave: this._onLegendTootipLeave.bind(this),
            };
            if (['bar', 'line'].includes(this.props.mode)) {
                let referenceColor;
                if (this.props.mode === 'bar') {
                    referenceColor = 'backgroundColor';
                } else {
                    referenceColor = 'borderColor';
                }
                legendOptions.labels = {
                    generateLabels: chart => {
                        const data = chart.data;
                        return data.datasets.map((dataset, i) => {
                            return {
                                text: this._shortenLabel(dataset.label),
                                fullText: dataset.label,
                                fillStyle: dataset[referenceColor],
                                hidden: !chart.isDatasetVisible(i),
                                lineCap: dataset.borderCapStyle,
                                lineDash: dataset.borderDash,
                                lineDashOffset: dataset.borderDashOffset,
                                lineJoin: dataset.borderJoinStyle,
                                lineWidth: dataset.borderWidth,
                                strokeStyle: dataset[referenceColor],
                                pointStyle: dataset.pointStyle,
                                datasetIndex: i,
                            };
                        });
                    },
                };
            } else {
                legendOptions.labels = {
                    generateLabels: chart => {
                        const data = chart.data;
                        const metaData = data.datasets.map((dataset, index) => {
                            return chart.getDatasetMeta(index).data;
                        });
                        return data.labels.map((label, i) => {
                            let hidden = false;
                            for (const data of metaData) {
                                if (data[i] && data[i].hidden) {
                                    hidden = true;
                                    break;
                                }
                            }
                            const fullText = this._relabelling(label);
                            const text = this._shortenLabel(fullText);
                            return {
                                text: text,
                                fullText: fullText,
                                fillStyle: label.isNoData ? '#d3d3d3' : this._getColor(i),
                                hidden: hidden,
                                index: i,
                            };
                        });
                    },
                };
            }
            return legendOptions;
        }

        /**
         * Returns the options used to generate the chart axes.
         *
         * @private
         * @returns {Object}
         */
        _getScaleOptions() {
            if (['bar', 'line'].includes(this.props.mode)) {
                return {
                    xAxes: [{
                        type: 'category',
                        scaleLabel: {
                            display: this.props.processedGroupBy.length && !this.props.isEmbedded,
                            labelString: this.props.processedGroupBy.length ?
                                this.props.fields[this.props.processedGroupBy[0].split(':')[0]].string : '',
                        },
                        ticks: {
                            // don't use bind:  callback is called with 'index' as second parameter
                            // with value labels.indexOf(label)!
                            callback: label => {
                                return this._relabelling(label);
                            },
                        },
                    }],
                    yAxes: [{
                        type: 'linear',
                        scaleLabel: {
                            display: !this.props.isEmbedded,
                            labelString: this.props.fields[this.props.measure].string,
                        },
                        ticks: {
                            callback: this._formatValue.bind(this),
                            suggestedMax: 0,
                            suggestedMin: 0,
                        }
                    }],
                };
            }
            return {};
        }

        /**
         * Extracts the important information from a tooltipItem generated by Charts.js
         * (a tooltip item corresponds to a line (different from measure name) of a tooltip)
         *
         * @private
         * @param {Object} item
         * @param {Object} data
         * @returns {Object}
         */
        _getTooltipItemContent(item, data) {
            const dataset = data.datasets[item.datasetIndex];
            let label = data.labels[item.index];
            let value;
            let boxColor;
            if (this.props.mode === 'bar') {
                label = this._relabelling(label, dataset.originIndex);
                if (this.props.processedGroupBy.length > 1 || this.props.origins.length > 1) {
                    label = label + "/" + dataset.label;
                }
                value = this._formatValue(item.yLabel);
                boxColor = dataset.backgroundColor;
            } else if (this.props.mode === 'line') {
                label = this._relabelling(label, dataset.originIndex);
                if (this.props.processedGroupBy.length > 1 || this.props.origins.length > 1) {
                    label = label + "/" + dataset.label;
                }
                value = this._formatValue(item.yLabel);
                boxColor = dataset.borderColor;
            } else {
                if (label.isNoData) {
                    value = this._formatValue(0);
                } else {
                    value = this._formatValue(dataset.data[item.index]);
                }
                label = this._relabelling(label, dataset.originIndex);
                if (this.props.origins.length > 1) {
                    label = dataset.label + "/" + label;
                }
                boxColor = dataset.backgroundColor[item.index];
            }
            return {
                label: label,
                value: value,
                boxColor: boxColor,
            };
        }

        /**
         * This function extracts the information from the data points in tooltipModel.dataPoints
         * (corresponding to datapoints over a given label determined by the mouse position)
         * that will be displayed in a custom tooltip.
         *
         * @private
         * @param {Object} tooltipModel see chartjs documentation
         * @return {Object[]}
         */
        _getTooltipItems(tooltipModel) {
            const data = this.chart.config.data;

            const orderedItems = tooltipModel.dataPoints.sort((dPt1, dPt2) => {
                return dPt2.yLabel - dPt1.yLabel;
            });

            const tooltipItems = [];
            for (const item of orderedItems) {
                tooltipItems.push(this._getTooltipItemContent(item, data))
            }
            return tooltipItems;
        }

        /**
         * Returns the options used to generate chart tooltips.
         *
         * @private
         * @returns {Object}
         */
        _getTooltipOptions() {
            const tooltipOptions = {
                // disable Chart.js tooltips
                enabled: false,
                custom: this._customTooltip.bind(this),
            };
            if (this.props.mode === 'line') {
                tooltipOptions.mode = 'index';
                tooltipOptions.intersect = false;
            }
            return tooltipOptions;
        }

        _hexToRGBA(hex, opacity) {
            const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
            const rgb = result.slice(1, 4).map(n => {
                return parseInt(n, 16);
            }).join(',');
            return 'rgba(' + rgb + ',' + opacity + ')';
        }

        /**
         * Return the first index of the array list where label can be found
         * or -1.
         *
         * @private
         * @param {Array[]} list
         * @param {Array} label
         * @returns {number}
         */
        _indexOf(list, label) {
            let index = -1;
            for (let j = 0; j < list.length; j++) {
                const otherLabel = list[j];
                if (label.length === otherLabel.length) {
                    var equal = true;
                    for (let i = 0; i < label.length; i++) {
                        if (label[i] !== otherLabel[i]) {
                            equal = false;
                        }
                    }
                    if (equal) {
                        index = j;
                        break;
                    }
                }
            }
            return index;
        }

        /**
         * Returns true iff the current graph can be clicked on to redirect to the
         * list of records.
         *
         * @private
         * @returns {boolean}
         */
        _isRedirectionEnabled() {
            return !this.props.disableLinking &&
                   (this.props.mode === 'bar' || this.props.mode === 'pie');
        }

        _prepareData(dataPoints) {
            const labelMap = {};
            const labels = [];
            for (const dataPt of dataPoints) {
                const label = this._getLabel(dataPt);
                const labelKey = dataPt.resId + ':' + JSON.stringify(label);
                const index = labelMap[labelKey];
                if (index === undefined) {
                    labelMap[labelKey] = dataPt.labelIndex = labels.length;
                    labels.push(label);
                }
                else{
                    dataPt.labelIndex = index;
                }
            }

            const newDataset = (datasetLabel, originIndex) => {
                const data = new Array(this._getDatasetDataLength(originIndex, labels.length)).fill(0);
                const domain = new Array(this._getDatasetDataLength(originIndex, labels.length)).fill([]);
                return {
                    label: datasetLabel,
                    data: data,
                    domain: domain,
                    originIndex: originIndex,
                };
            };

            // dataPoints --> datasets
            const datasetsTmp = {};
            for (const dp of dataPoints) {
                const datasetLabel = this._getDatasetLabel(dp);
                if (!(datasetLabel in datasetsTmp)){
                    datasetsTmp[datasetLabel] = newDataset(datasetLabel, dp.originIndex);
                }
                const labelIndex = dp.labelIndex;
                datasetsTmp[datasetLabel].data[labelIndex] = dp.value;
                datasetsTmp[datasetLabel].domain[labelIndex] = dp.domain;
            }
            const datasets = Object.values(datasetsTmp);

            // sort by origin
            datasets.sort((dataset1, dataset2) => {
                return dataset1.originIndex - dataset2.originIndex;
            });

            return {
                datasets: datasets,
                labels: labels,
            };
        }

        /**
         * Prepare options for the chart according to the current mode (= chart type).
         * This function returns the parameter options used to instantiate the chart
         *
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
                options.onClick = this._onGraphClicked.bind(this);
            }
            return options;
        }

        /**
         * Determine how to relabel a label according to a given origin.
         * The idea is that the getLabel function is in general not invertible but
         * it is when restricted to the set of dataPoints coming from a same origin.

         * @private
         * @param {Array} label
         * @param {Array} originIndex
         * @returns {string}
         */
        _relabelling(label, originIndex) {
            if (label.isNoData) {
                return label[0];
            }
            const i = this.props.comparisonFieldIndex;
            if (['bar', 'line'].includes(this.props.mode) && i === 0) {
                // here label is an array of length 1 and contains a number
                return this.dateClasses.representative(label, originIndex) || '';
            } else if (this.props.mode === 'pie' && i === 0) {
                // here label is an array of length at least one containing string or numbers
                const labelCopy = label.slice(0);
                if (originIndex !== undefined) {
                    labelCopy.splice(i, 1, this.dateClasses.representative(label[i], originIndex));
                } else {
                    labelCopy.splice(i, 1, this.dateClasses.dateClassMembers(label[i]));
                }
                return labelCopy.join('/');
            }
            // here label is an array containing strings or numbers.
            return label.join('/') || _t('Total');
        }

        /**
         * create bar chart.
         *
         * @private
         * @param {Object[]} dataPoints
         */
        _renderBarChart(dataPoints) {
            // prepare data
            const data = this._prepareData(dataPoints);

            for (let index = 0; index < data.datasets.length; ++index) {
                const dataset = data.datasets[index];
                // used when stacked
                dataset.stack = this.props.stacked ? this.props.origins[dataset.originIndex] : undefined;
                // set dataset color
                var color = this._getColor(index);
                dataset.backgroundColor = color;
            }

            // prepare options
            const options = this._prepareOptions(data.datasets.length);

            // create chart
            const ctx = this.canvasRef.el;
            this.chart = new Chart(ctx, {
                type: 'bar',
                data: data,
                options: options,
            });
        }

        /**
         * Render the chart if no message error is already displayed.
         *
         * @private
         */
        _renderChart() {
            if (this.chart) {
                this.chart.destroy();
            }

            if (this.noContentHelperData.show){
                return;
            }

            let dataPoints = this.filteredDataPoints;
            dataPoints = this._sortDataPoints(dataPoints);
            var i = this.props.comparisonFieldIndex;
            if (i === 0) {
                this.dateClasses = this._getDateClasses(dataPoints);
            }

            switch (this.props.mode) {
                case 'bar':
                    this._renderBarChart(dataPoints);
                    break;
                case 'line':
                    this._renderLineChart(dataPoints);
                    break;
                case 'pie':
                    this._renderPieChart(dataPoints);
                    break;
            }
        }

        /**
         * create line chart.
         *
         * @private
         * @param {Object[]} dataPoints
         */
        _renderLineChart(dataPoints) {
            // prepare data
            const data = this._prepareData(dataPoints);
            for (let index = 0; index < data.datasets.length; ++index) {
                const dataset = data.datasets[index];
                if (this.props.processedGroupBy.length <= 1 && this.props.origins.length > 1) {
                    if (dataset.originIndex === 0) {
                        dataset.fill = 'origin';
                        dataset.backgroundColor = this._hexToRGBA(COLORS[0], 0.4);
                        dataset.borderColor = this._hexToRGBA(COLORS[0], 1);
                    } else if (dataset.originIndex === 1) {
                        dataset.borderColor = this._hexToRGBA(COLORS[1], 1);
                    } else {
                        dataset.borderColor = this._getColor(index);
                    }
                } else {
                    dataset.borderColor = this._getColor(index);
                }
                if (data.labels.length === 1) {
                    // shift of the real value to right. This is done to center the points in the chart
                    // See data.labels below in Chart parameters
                    dataset.data.unshift(undefined);
                }
                dataset.pointBackgroundColor = dataset.borderColor;
                dataset.pointBorderColor = 'rgba(0,0,0,0.2)';
            }

            if (data.datasets.length === 1) {
                const dataset = data.datasets[0];
                dataset.fill = 'origin';
                dataset.backgroundColor = this._hexToRGBA(COLORS[0], 0.4);
            }

            // center the points in the chart (without that code they are put on the left and the graph seems empty)
            data.labels = data.labels.length > 1 ?
                data.labels :
                Array.prototype.concat.apply([], [[['']], data.labels, [['']]]);

            // prepare options
            const options = this._prepareOptions(data.datasets.length);

            // create chart
            const ctx = this.canvasRef.el;
            this.chart = new Chart(ctx, {
                type: 'line',
                data: data,
                options: options,
            });
        }

         /**
         * create pie chart
         *
         * @private
         * @param {Object[]} dataPoints
         */
        _renderPieChart(dataPoints) {
            // try to see if some pathologies are still present after the filtering
            let allZero = true;
            for (const datapt of dataPoints) {
                allZero = allZero && (datapt.value === 0);
            };

            // prepare data
            let data = {};
            let colors = [];
            if (allZero) {
                // add fake data to display a pie chart with a grey zone associated
                // with every origin
                data.labels = [NO_DATA];
                data.datasets = this.props.origins.map(origin => {
                    return {
                        label: origin,
                        data: [1],
                        backgroundColor: ['#d3d3d3'],
                    };
                });
            } else {
                data = this._prepareData(dataPoints);
                // give same color to same groups from different origins
                colors = data.labels.map((label, index) => {
                    return this._getColor(index);
                });
                for (const dataset of data.datasets) {
                    dataset.backgroundColor = colors;
                    dataset.borderColor = 'rgba(255,255,255,0.6)';
                }
                // make sure there is a zone associated with every origin
                const representedOriginIndexes = data.datasets.map(dataset => {
                    return dataset.originIndex;
                });
                let addNoDataToLegend = false;
                const fakeData = (new Array(data.labels.length)).concat([1]);

                for (let originIndex = 0; originIndex < this.props.origins.length; ++originIndex) {
                    const origin = this.props.origins[originIndex];
                    if (!representedOriginIndexes.includes(originIndex)) {
                        data.datasets.splice(originIndex, 0, {
                            label: origin,
                            data: fakeData,
                            backgroundColor: colors.concat(['#d3d3d3']),
                        });
                        addNoDataToLegend = true;
                    }
                }
                if (addNoDataToLegend) {
                    data.labels.push(NO_DATA);
                }
            }

            // prepare options
            const options = this._prepareOptions(data.datasets.length);

            // create chart
            const ctx = this.canvasRef.el;
            this.chart = new Chart(ctx, {
                type: 'pie',
                data: data,
                options: options,
            });
        }

        /**
         * Determine whether the data are good, and display an error message
         * if this is not the case.
         * @private
         * @param {Object} props
         */
        _setNoContentHelper(props) {
            this.noContentHelperData.show = false;

            const dataPoints = this.filteredDataPoints;
            if (!dataPoints.length && props.mode !== 'pie') {
                this.noContentHelperData.show = true;
                this.noContentHelperData.title = "";
                this.noContentHelperData.description = "";
            } else if (props.mode == 'pie') {
                let allNegative = true;
                let someNegative = false;
                let allZero = true;
                for (const datapt of props.dataPoints) {
                    allNegative = allNegative && (datapt.value < 0);
                    someNegative = someNegative || (datapt.value < 0);
                    allZero = allZero && (datapt.value === 0);
                };

                if (someNegative && !allNegative) {
                    const title = _t("Invalid data")
                    const message = _t("Pie chart cannot mix positive and negative numbers. ") +
                              _t("Try to change your domain to only display positive results");
                    this.noContentHelperData.show = true;
                    this.noContentHelperData.title = title;
                    this.noContentHelperData.description = message;
                    return;
                }
                if (allZero && !this.props.isEmbedded && this.props.origins.length === 1) {
                    const title = _("Invalid data");
                    const message = _t("Pie chart cannot display all zero numbers. ") +
                            _t("Try to change your domain to display positive results");
                    this.noContentHelperData.show = true;
                    this.noContentHelperData.title = title;
                    this.noContentHelperData.description = message;
                    return;
                }
            }
        }

        /**
         * Used to avoid too long legend items
         *
         * @private
         * @param {string} label
         * @returns {string} shortened version of the input label
         */
        _shortenLabel(label) {
            // string returned could be 'wrong' if a groupby value contain a '/'!
            const groups = label.split("/");
            let shortLabel = groups.slice(0, 3).join("/");
            if (shortLabel.length > 30) {
                shortLabel = shortLabel.slice(0, 30) + '...';
            } else if (groups.length > 3) {
                shortLabel = shortLabel + '/...';
            }
            return shortLabel;
        }

        /**
         * Sort datapoints according to the current order (ASC or DESC).
         *
         * Note: this should be moved to the model at some point.
         *
         * @private
         * @param {Object[]} dataPoints
         * @returns {Object[]} sorted dataPoints if orderby set on state
         */
        _sortDataPoints(dataPoints) {
            if (!Object.keys(this.props.timeRanges).length && this.props.orderBy &&
                ['bar', 'line'].includes(this.props.mode) && this.props.groupBy.length) {
                // group data by their x-axis value, and then sort datapoints
                // based on the sum of values by group in ascending/descending order
                const groupByFieldName = this.props.groupBy[0].split(':')[0];
                const groupedByMany2One = this.props.fields[groupByFieldName].type === 'many2one';
                const groupedDataPoints = {};
                dataPoints.forEach(function (dataPoint) {
                    const key = groupedByMany2One ? dataPoint.resId : dataPoint.labels[0];
                    groupedDataPoints[key] = groupedDataPoints[key] || [];
                    groupedDataPoints[key].push(dataPoint);
                });
                dataPoints = _.sortBy(groupedDataPoints, function (group) {
                    return group.reduce((sum, dataPoint) => sum + dataPoint.value, 0);
                });
                dataPoints = dataPoints.flat();
                if (this.props.orderBy === 'desc') {
                    dataPoints = dataPoints.reverse('value');
                }
            }
            return dataPoints;
        }

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * @private
         * @param {MouseEvent} ev
         */
        _onGraphClicked(ev) {
            const activeElement = this.chart.getElementAtEvent(ev);
            if (activeElement.length === 0) {
                return;
            }
            const domain = this.chart.data.datasets[activeElement[0]._datasetIndex].domain;
            if (!domain) {
                return; // empty dataset
            }
            this.trigger('open_view', {
                domain: domain[activeElement[0]._index],
            });
        }

        /**
         * If the text of a legend item has been shortened and the user mouse over
         * that item (actually the event type is mousemove), a tooltip with the item
         * full text is displayed.
         *
         * @private
         * @param {MouseEvent} e
         * @param {Object} legendItem
         */
        _onlegendTooltipHover(e, legendItem) {
            // The string legendItem.text is an initial segment of legendItem.fullText.
            // If the two coincide, no need to generate a tooltip.
            // If a tooltip for the legend already exists, it is already good and don't need
            // to be recreated.
            if (legendItem.text === legendItem.fullText || this.legendTooltip) {
                return;
            }

            const chartAreaLeft = this.chart.chartArea.left;
            const chartAreaRight = this.chart.chartArea.right;
            const rendererTop = this.el.getBoundingClientRect().top;

            this.legendTooltip = document.createElement('div');
            this.legendTooltip.className = 'o_tooltip_legend';
            this.legendTooltip.innerText = legendItem.fullText;
            this.legendTooltip.style["top"] = (e.clientY - rendererTop) + 'px';
            this.legendTooltip.style["maxWidth"] = Math.floor((chartAreaRight - chartAreaLeft) / 1.68) + 'px';

            const container = this.el.querySelector('.o_graph_canvas_container')
            container.appendChild(this.legendTooltip);

            this._fixTooltipLeftPosition(this.legendTooltip, e.clientX);
        }

        /**
         * If there's a legend tooltip and the user mouse out of the corresponding
         * legend item, the tooltip is removed.
         *
         * @private
         */
        _onLegendTootipLeave() {
            if (this.legendTooltip) {
                this.legendTooltip.remove();
                this.legendTooltip = null;
            }
        }
    }

    GraphOwlRenderer.template = 'web.GraphOwlRenderer';

    return GraphOwlRenderer;

});
