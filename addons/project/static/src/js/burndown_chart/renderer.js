/** @odoo-module alias=project.BurndownChartRenderer **/
import * as GraphRenderer from 'web/static/src/js/views/graph/graph_renderer';

const {
    hexToRGBA,
} = require("web/static/src/js/views/graph/graph_utils");

export class BurndownChartRenderer extends GraphRenderer {
    /**
     * @override
     * @private
     */
    _createLineChartConfig() {
        const { data, options, type } = super._createLineChartConfig();
        for (const dataset of data.datasets) {
            if (this.props.stacked) {
                dataset.backgroundColor = hexToRGBA(dataset.borderColor, 0.4);
            }
        }
        return { data, options, type };
    }

    /**
     * @override
     * @private
     * @returns {Object}
     */
    _getElementOptions() {
        const elementOptions = super._getElementOptions();
        if (this.props.mode === 'line') {
            elementOptions.line.fill = this.props.stacked;
        }
        return elementOptions;
    }

    /**
     * @override
     * @private
     */
    _getScaleOptions() {
        const scaleOptions = super._getScaleOptions();
        if (this.props.mode !== "line") {
            return scaleOptions;
        }

        const { xAxes, yAxes } = scaleOptions;
        for (const y of yAxes) {
            y.stacked = this.props.stacked;
        }
        return { xAxes, yAxes };
    }
}
