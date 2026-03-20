import { Domain } from "@web/core/domain";
import { ChartDataSource, chartTypeToDataSourceMode } from "../data_source/chart_data_source";
import { OdooUIPlugin } from "@spreadsheet/plugins";
import { deepEqual } from "@web/core/utils/objects";

export class OdooChartCoreViewPlugin extends OdooUIPlugin {
    static getters = /** @type {const} */ (["getChartDataSource", "getOdooEnv"]);

    shouldChartUpdateReloadDataSource = false;

    constructor(config) {
        super(config);

        this.custom = config.custom;

        /** @type {Record<string, ChartDataSource>} */
        this.charts = {};
    }

    beforeHandle(cmd) {
        switch (cmd.type) {
            case "START":
                for (const chartId of this.getters.getOdooChartIds()) {
                    this._setupChartDataSource(chartId);
                }

                // make sure the domains are correctly set before
                // any evaluation
                this._addDomains();
                break;
            case "UPDATE_CHART": {
                if (cmd.definition.type.startsWith("odoo_")) {
                    const chart = this.getters.getChart(cmd.chartId);
                    if (this._shouldReloadDataSource(cmd.chartId, cmd.definition)) {
                        this.shouldChartUpdateReloadDataSource = true;
                    } else if (cmd.definition.type !== chart.type) {
                        const dataSource = this.getChartDataSource(cmd.chartId);
                        dataSource.changeChartType(chartTypeToDataSourceMode(cmd.definition.type));
                    }
                }
                break;
            }
        }
    }

    /**
     * Handle a spreadsheet command
     *
     * @param {Object} cmd Command
     */
    handle(cmd) {
        switch (cmd.type) {
            case "CREATE_CHART": {
                if (cmd.definition.type.startsWith("odoo_")) {
                    this._setupChartDataSource(cmd.chartId);
                }
                break;
            }
            case "UPDATE_CHART": {
                if (cmd.definition.type.startsWith("odoo_")) {
                    if (this.shouldChartUpdateReloadDataSource) {
                        this._resetChartDataSource(cmd.chartId);
                        this.shouldChartUpdateReloadDataSource = false;
                    }
                    this._setChartDataSource(cmd.chartId);
                }
                break;
            }
            case "ADD_GLOBAL_FILTER":
            case "EDIT_GLOBAL_FILTER":
            case "REMOVE_GLOBAL_FILTER":
            case "SET_GLOBAL_FILTER_VALUE":
                this._addDomains();
                break;
            case "UNDO":
            case "REDO": {
                if (
                    cmd.commands.find((command) =>
                        [
                            "ADD_GLOBAL_FILTER",
                            "EDIT_GLOBAL_FILTER",
                            "REMOVE_GLOBAL_FILTER",
                        ].includes(command.type)
                    )
                ) {
                    this._addDomains();
                }

                const domainEditionCommands = cmd.commands.filter(
                    (cmd) => cmd.type === "UPDATE_CHART" || cmd.type === "CREATE_CHART"
                );
                for (const cmd of domainEditionCommands) {
                    if (!this.getters.getOdooChartIds().includes(cmd.chartId)) {
                        continue;
                    }
                    if (this._shouldReloadDataSource(cmd.chartId, cmd.definition)) {
                        this._resetChartDataSource(cmd.chartId);
                    }
                }
                break;
            }
            case "REFRESH_ALL_DATA_SOURCES":
                this._refreshOdooCharts();
                break;
        }
    }

    /**
     * @param {string} chartId
     * @returns {ChartDataSource|undefined}
     */
    getChartDataSource(chartId) {
        const dataSourceId = this._getOdooChartDataSourceId(chartId);
        return this.charts[dataSourceId];
    }

    getOdooEnv() {
        return this.custom.env;
    }

    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------

    /**
     * Add an additional domain to a chart
     *
     * @private
     *
     * @param {string} chartId chart id
     */
    _addDomain(chartId) {
        const domainList = [];
        for (const [filterId, fieldMatch] of Object.entries(
            this.getters.getChartFieldMatch(chartId)
        )) {
            domainList.push(this.getters.getGlobalFilterDomain(filterId, fieldMatch));
        }
        const domain = Domain.combine(domainList, "AND").toString();
        this.getChartDataSource(chartId).addDomain(domain);
    }

    /**
     * Add an additional domain to all chart
     *
     * @private
     *
     */
    _addDomains() {
        for (const chartId of this.getters.getOdooChartIds()) {
            // Reset the data source to prevent eager loading
            // of the data source when the domain is added
            this._resetChartDataSource(chartId);
        }
    }

    /**
     * @param {string} chartId
     * @param {string} dataSourceId
     */
    _setupChartDataSource(chartId) {
        const dataSourceId = this._getOdooChartDataSourceId(chartId);
        if (!(dataSourceId in this.charts)) {
            this._resetChartDataSource(chartId);
        }
    }

    /**
     * Sets the datasource on the corresponding chart
     * @param {string} chartId
     */
    _resetChartDataSource(chartId) {
        const definition = this.getters.getChart(chartId).getDefinitionForDataSource();
        const dataSourceId = this._getOdooChartDataSourceId(chartId);
        this.charts[dataSourceId] = new ChartDataSource(this.custom, definition);
        this._addDomain(chartId);
        this._setChartDataSource(chartId);
    }

    /**
     * Sets the datasource on the corresponding chart
     * @param {string} chartId
     */
    _setChartDataSource(chartId) {
        const chart = this.getters.getChart(chartId);
        chart.setDataSource(this.getChartDataSource(chartId));
    }

    _getOdooChartDataSourceId(chartId) {
        return `chart-${chartId}`;
    }

    /**
     * Refresh the cache of a chart
     * @param {string} chartId Id of the chart
     */
    _refreshOdooChart(chartId) {
        this.getChartDataSource(chartId).load({ reload: true });
    }

    /**
     * Refresh the cache of all the charts
     */
    _refreshOdooCharts() {
        for (const chartId of this.getters.getOdooChartIds()) {
            this._refreshOdooChart(chartId);
        }
    }

    _shouldReloadDataSource(chartId, definition) {
        const chart = this.getters.getChart(chartId);
        const dataSource = this.getChartDataSource(chartId);
        return (
            !deepEqual(chart.searchParams.groupBy, definition.searchParams.groupBy) ||
            chart.metaData.cumulated !== definition.cumulative ||
            chart.cumulatedStart !== definition.cumulatedStart ||
            dataSource.getInitialDomainString() !==
                new Domain(definition.searchParams.domain).toString()
        );
    }
}
