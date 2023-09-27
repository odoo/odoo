/** @odoo-module */
import * as spreadsheet from "@odoo/o-spreadsheet";
import { globalFiltersFieldMatchers } from "@spreadsheet/global_filters/plugins/global_filters_core_plugin";
import { checkFilterFieldMatching } from "@spreadsheet/global_filters/helpers";
import CommandResult from "../../o_spreadsheet/cancelled_reason";
import { loadJS } from "@web/core/assets";
import { odooChartToImage } from "../../helpers/model";

const { CorePlugin } = spreadsheet;
const { chartRegistry } = spreadsheet.registries;

/**
 * @typedef {Object} Chart
 * @property {Object} fieldMatching
 *
 * @typedef {import("@spreadsheet/global_filters/plugins/global_filters_core_plugin").FieldMatching} FieldMatching
 */

export default class OdooChartCorePlugin extends CorePlugin {
    constructor(config) {
        super(config);

        /** @type {Object.<string, Chart>} */
        this.charts = {};

        globalFiltersFieldMatchers["chart"] = {
            geIds: () => this.getters.getOdooChartIds(),
            getDisplayName: (chartId) => this.getters.getOdooChartDisplayName(chartId),
            getFieldMatching: (chartId, filterId) =>
                this.getOdooChartFieldMatching(chartId, filterId),
            getModel: (chartId) =>
                this.getters.getChart(chartId).getDefinitionForDataSource().metaData.resModel,
        };
    }

    allowDispatch(cmd) {
        switch (cmd.type) {
            case "ADD_GLOBAL_FILTER":
            case "EDIT_GLOBAL_FILTER":
                if (cmd.chart) {
                    return checkFilterFieldMatching(cmd.chart);
                }
        }
        return CommandResult.Success;
    }

    /**
     * Handle a spreadsheet command
     *
     * @param {Object} cmd Command
     */
    handle(cmd) {
        switch (cmd.type) {
            case "CREATE_CHART": {
                switch (cmd.definition.type) {
                    case "odoo_pie":
                    case "odoo_bar":
                    case "odoo_line":
                        this._addOdooChart(cmd.id);
                        break;
                }
                break;
            }
            case "DELETE_FIGURE": {
                const charts = { ...this.charts };
                delete charts[cmd.id];
                this.history.update("charts", charts);
                break;
            }
            case "REMOVE_GLOBAL_FILTER":
                this._onFilterDeletion(cmd.id);
                break;
            case "ADD_GLOBAL_FILTER":
            case "EDIT_GLOBAL_FILTER":
                if (cmd.chart) {
                    this._setOdooChartFieldMatching(cmd.filter.id, cmd.chart);
                }
                break;
        }
    }

    // -------------------------------------------------------------------------
    // Getters
    // -------------------------------------------------------------------------

    /**
     * Get all the odoo chart ids
     * @returns {Array<string>}
     */
    getOdooChartIds() {
        const ids = [];
        for (const sheetId of this.getters.getSheetIds()) {
            ids.push(
                ...this.getters
                    .getChartIds(sheetId)
                    .filter((id) => this.getters.getChartType(id).startsWith("odoo_"))
            );
        }
        return ids;
    }

    /**
     * @param {string} chartId
     * @returns {string}
     */
    getChartFieldMatch(chartId) {
        return this.charts[chartId].fieldMatching;
    }

    /**
     *
     * @param {string} chartId
     * @returns {string}
     */
    getOdooChartDisplayName(chartId) {
        return this.getters.getChart(chartId).title;
    }

    /**
     * Import the pivots
     *
     * @param {Object} data
     */
    import(data) {
        for (const sheet of data.sheets) {
            if (sheet.figures) {
                for (const figure of sheet.figures) {
                    if (figure.tag === "chart" && figure.data.type.startsWith("odoo_")) {
                        this._addOdooChart(figure.id, figure.data.fieldMatching);
                    }
                }
            }
        }
    }
    /**
     * Export the pivots
     *
     * @param {Object} data
     */
    export(data) {
        for (const sheet of data.sheets) {
            if (sheet.figures) {
                for (const figure of sheet.figures) {
                    if (figure.tag === "chart" && figure.data.type.startsWith("odoo_")) {
                        figure.data.fieldMatching = this.getChartFieldMatch(figure.id);
                    }
                }
            }
        }
    }
    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------

    /**
     * Get the current pivotFieldMatching of a chart
     *
     * @param {string} chartId
     * @param {string} filterId
     */
    getOdooChartFieldMatching(chartId, filterId) {
        return this.charts[chartId].fieldMatching[filterId];
    }

    /**
     * Sets the current pivotFieldMatching of a chart
     *
     * @param {string} filterId
     * @param {Record<string,FieldMatching>} chartFieldMatches
     */
    _setOdooChartFieldMatching(filterId, chartFieldMatches) {
        const charts = { ...this.charts };
        for (const [chartId, fieldMatch] of Object.entries(chartFieldMatches)) {
            charts[chartId].fieldMatching[filterId] = fieldMatch;
        }
        this.history.update("charts", charts);
    }

    _onFilterDeletion(filterId) {
        const charts = { ...this.charts };
        for (const chartId in charts) {
            this.history.update("charts", chartId, "fieldMatching", filterId, undefined);
        }
    }

    /**
     * @param {string} chartId
     * @param {Object} fieldMatching
     */
    _addOdooChart(chartId, fieldMatching = {}) {
        const charts = { ...this.charts };
        charts[chartId] = {
            fieldMatching,
        };
        this.history.update("charts", charts);
    }

    exportForExcel(data) {
        for (let sheet of data.sheets) {
            const images = [];
            for (const figure of sheet.figures) {
                if (!figure || figure.tag !== "chart") {
                    continue;
                }
                const figureId = figure.id;
                const type = this.getters.getChartType(figureId);
                if (type.startsWith("odoo_")) {
                    loadJS("/web/static/lib/Chart/Chart.js");
                    const chart = this.getters.getChart(figureId);
                    const runtime = chartRegistry.get(type).getChartRuntime(chart);
                    const img = odooChartToImage(runtime, figure);
                    images.push({
                        ...figure,
                        tag: "image",
                        data: {
                            mimetype:"image/png",
                            path: img,
                            size: { width: figure.width, height: figure.height },
                        }
                    });
                }
            }
            sheet.images = [...sheet.images, ...images];
        }
        return data;
    }

}

OdooChartCorePlugin.getters = [
    "getOdooChartIds",
    "getChartFieldMatch",
    "getOdooChartDisplayName",
    "getOdooChartFieldMatching",
];
