/** @odoo-module **/

import { isCSSColor } from '@web/core/utils/colors';
import weUtils from "@web_editor/js/common/utils";
import {
    SnippetOption,
    SnippetOptionComponent,
} from "@web_editor/js/editor/snippets.options";
import {
    registerWebsiteOption,
} from "@website/js/editor/snippets.registry";

class InnerChartOptionComponent extends SnippetOptionComponent {
    static themeArray = ['o-color-1', 'o-color-2', 'o-color-3', 'o-color-4', 'o-color-5'];
    onAddDataset() {
        const usedColor = this.renderContext.datasets.map(dataset => dataset.backgroundColor);
        const color = this.constructor.themeArray.filter(el => !usedColor.includes(el))[0] || this._randomColor();
        this.renderContext.datasets.push({
            label: "",
            data: [],
            backgroundColor: color,
            borderColor: color,
        });
        this.env.snippetOption._reloadGraph();
    }
    onAddRow() {
        this.renderContext.labels.push("");
        this.env.snippetOption._reloadGraph();
    }
    onRemoveDataset(datasetIndex) {
        this.renderContext.datasets.splice(datasetIndex, 1);
        this.env.snippetOption._reloadGraph();
        this._refreshDatasetPalette()
    }
    onRemoveRow(labelIndex) {
        this.renderContext.labels.splice(labelIndex, 1);
        for (const dataset of this.renderContext.datasets) {
            dataset.data.splice(labelIndex, 1);
        }
        this.env.snippetOption._reloadGraph();
    }
    onCellFocus(datasetIndex, labelIndex) {
        this.renderContext.focusedDatasetIndex = datasetIndex;
        this.renderContext.focusedLabelIndex = labelIndex;
        this._refreshDatasetPalette()
    }
    setDatasetLabel(datasetIndex, datasetLabel) {
        this.renderContext.datasets[datasetIndex].label = datasetLabel;
        this.env.snippetOption._reloadGraph();
    }
    setRowLabel(rowIndex, rowLabel) {
        this.renderContext.labels[rowIndex] = rowLabel;
        this.env.snippetOption._reloadGraph();
    }
    setCellValue(datasetIndex, rowIndex, value) {
        this.renderContext.datasets[datasetIndex].data[rowIndex] = value;
        this.env.snippetOption._reloadGraph();
    }
    isCSSColor(color) {
        return isCSSColor(color);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _refreshDatasetPalette() {
        // TODO: @owl-options how am I supposed to refresh those ?
        /*
        this.env.userValueNotification({
            triggerWidgetsNames: ["chart_bg_color_opt", "chart_border_color_opt"],
        });
        */
        this.env.snippetOption.updateUI();
    }
    /**
     * Return a random hexadecimal color.
     *
     * @private
     * @return {string}
     */
    _randomColor() {
        return '#' + ('00000' + (Math.random() * (1 << 24) | 0).toString(16)).slice(-6).toUpperCase();
    }
}

class InnerChart extends SnippetOption {
    static themeArray = ['o-color-1', 'o-color-2', 'o-color-3', 'o-color-4', 'o-color-5'];
    /*
    custom_events: Object.assign({}, options.Class.prototype.custom_events, {
        'get_custom_colors': '_onGetCustomColors',
    }),
    */
    /**
     * @override
     */
    constructor() {
        super(...arguments);
        this.style = window.getComputedStyle(this.$target[0].ownerDocument.documentElement);
    }
    /**
     * @override
     */
    async willStart() {
        await super.willStart(...arguments);

        // Build matrix content
        const data = JSON.parse(this.$target[0].dataset.data);
        Object.assign(data, {
            focusedDatasetIndex: -1,
            focusedLabelIndex: -1,
        }); 
        Object.assign(this.renderContext, data);
        data.datasets.forEach((dataset, i) => {
            if (this._isPieChart()) {
                // Add header colors in case the user changes the type of graph
                dataset.backgroundColor = this.themeArray[i] || this._randomColor();
                dataset.borderColor = this.themeArray[i] || this._randomColor();
            }
        });
    }

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Set the color on the selected input.
     */
    async colorChange(previewMode, widgetValue, params) {
        const dataset = this.renderContext.datasets[this.renderContext.focusedDatasetIndex];
        if (!dataset) {
            return;
        }
        if (widgetValue) {
            dataset[params.attributeName] = widgetValue;
        } else {
            delete dataset[params.attributeName];
        }
        await this._reloadGraph();
    }
    /**
     * @override
     */
    async selectDataAttribute(previewMode, widgetValue, params) {
        await super.selectDataAttribute(...arguments);
        // Data might change if going from or to a pieChart.
        if (params.attributeName === 'type') {
            await this._reloadGraph();
        }
        if (params.attributeName === 'minValue' || params.attributeName === 'maxValue') {
            this._computeTicksMinMaxValue();
        }
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
        if (methodName === 'colorChange') {
            const dataset = this.renderContext.datasets[this.renderContext.focusedDatasetIndex];
            return dataset && dataset[params.attributeName] || '';
        }
        return super._computeWidgetState(...arguments);
    }
    /**
     * @override
     */
    _computeWidgetVisibility(widgetName, params) {
        switch (widgetName) {
            case 'stacked_chart_opt': {
                return this._getColumnCount() > 1;
            }
            case 'chart_bg_color_opt':
            case 'chart_border_color_opt': {
                const dataset = this.renderContext.datasets[this.renderContext.focusedDatasetIndex];
                return !!dataset;
            }
        }
        return super._computeWidgetVisibility(...arguments);
    }
    /**
     * Maintains the gap between the scale axis for the auto fit behavior if we
     * used min/max config.
     *
     * @private
     */
    _computeTicksMinMaxValue() {
        const dataset = this.$target[0].dataset;
        let minValue = parseInt(dataset.minValue);
        let maxValue = parseInt(dataset.maxValue);
        if (!isNaN(maxValue)) {
            // Reverse min max values when min value is greater than max value
            if (maxValue < minValue) {
                maxValue = minValue;
                minValue = parseInt(dataset.maxValue);
            } else if (maxValue === minValue) {
                // If min value and max value are same for positive and negative
                // number
                minValue < 0 ? (maxValue = 0, minValue = 2 * minValue) : (minValue = 0, maxValue = 2 * maxValue);
            }
        } else {
            // Find max value from each row/column data
            const datasets = JSON.parse(dataset.data).datasets || [];
            const dataValue = datasets
                .map((el) => {
                    return el.data.map((data) => {
                        return !isNaN(parseInt(data)) ? parseInt(data) : 0;
                    });
                })
                .flat();
            // When max value is not given and min value is greater than chart
            // data values
            if (minValue >= Math.max(...dataValue)) {
                maxValue = minValue;
                minValue = 0;
            }
        }
        this.$target.attr({
            'data-ticks-min': minValue,
            'data-ticks-max': maxValue,
        });
    }
    /**
     * Sets and reloads the data on the canvas if it has changed.
     * Used in matrix related method.
     *
     * @private
     */
    async _reloadGraph() {
        const jsonValue = this._matrixToChartData();
        if (this.$target[0].dataset.data !== jsonValue) {
            this.$target[0].dataset.data = jsonValue;
            await this._refreshPublicWidgets();
        }
    }
    /**
     * Return a stringifyed chart.js data object from the matrix
     * Pie charts have one color per data while other charts have one color per dataset.
     *
     * @private
     */
    _matrixToChartData() {
        return JSON.stringify({
            labels: this.renderContext.labels,
            datasets: this.renderContext.datasets,
        });
    }
    /**
     * @private
     * @return {boolean}
     */
    _isPieChart() {
        return ['pie', 'doughnut'].includes(this.$target[0].dataset.type);
    }
    /**
     * Return the number of column minus header and button
     * @private
     * @return {integer}
     */
    _getColumnCount() {
        return this.renderContext.datasets.length;
    }
    /**
     * Return a random hexadecimal color.
     *
     * @private
     * @return {string}
     */
    _randomColor() {
        return '#' + ('00000' + (Math.random() * (1 << 24) | 0).toString(16)).slice(-6).toUpperCase();
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Used by colorPalette to retrieve the custom colors used on the chart
     * Make an array with all the custom colors used on the chart
     * and apply it to the onSuccess method provided by the trigger_up.
     *
     * @private
     */
    // TODO: @owl-options what was this mechanism replaced with ?
    _onGetCustomColors(ev) {
        const data = JSON.parse(this.$target[0].dataset.data || '');
        let customColors = [];
        data.datasets.forEach(el => {
            if (this._isPieChart()) {
                customColors = customColors.concat(el.backgroundColor).concat(el.borderColor);
            } else {
                customColors.push(el.backgroundColor);
                customColors.push(el.borderColor);
            }
        });
        customColors = customColors.filter((el, i, array) => {
            return !weUtils.getCSSVariableValue(el, this.style) && array.indexOf(el) === i && el !== ''; // unique non class not transparent
        });
        ev.data.onSuccess(customColors);
    }
}

registerWebsiteOption("InnerChart", {
    Class: InnerChart,
    renderingComponent: InnerChartOptionComponent,
    template: "website.s_chart_option",
    selector: ".s_chart",
    withColorCombinations: false,
});
