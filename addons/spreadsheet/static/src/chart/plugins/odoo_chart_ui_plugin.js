/** @odoo-module */

import * as spreadsheet from "@odoo/o-spreadsheet";
import { Domain } from "@web/core/domain";
import { globalFiltersFieldMatchers } from "@spreadsheet/global_filters/plugins/global_filters_core_plugin";
import { ChartDataSource } from "../data_source/chart_data_source";
import { sprintf } from "@web/core/utils/strings";
import { _t } from "@web/core/l10n/translation";

const { UIPlugin } = spreadsheet;

export class OdooChartUIPlugin extends UIPlugin {
    shouldChartUpdateReloadDataSource = false;

    constructor(config) {
        super(config);
        this.dataSources = config.custom.dataSources;

        globalFiltersFieldMatchers["chart"] = {
            ...globalFiltersFieldMatchers["chart"],
            getTag: async (chartId) => {
                const model = await this.getChartDataSource(chartId).getModelLabel();
                return sprintf(_t("Chart - %s"), model);
            },
            waitForReady: () => this._getOdooChartsWaitForReady(),
            getFields: (chartId) => this.getChartDataSource(chartId).getFields(),
        };
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
                switch (cmd.definition.type) {
                    case "odoo_pie":
                    case "odoo_bar":
                    case "odoo_line": {
                        const dataSource = this.getChartDataSource(cmd.id);
                        const chart = this.getters.getChart(cmd.id);
                        if (
                            cmd.definition.type !== chart.type ||
                            chart.cumulative !== cmd.definition.cumulative ||
                            dataSource.getInitialDomainString() !==
                                new Domain(cmd.definition.searchParams.domain).toString()
                        ) {
                            this.shouldChartUpdateReloadDataSource = true;
                        }
                        break;
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
                switch (cmd.definition.type) {
                    case "odoo_pie":
                    case "odoo_bar":
                    case "odoo_line":
                        this._setupChartDataSource(cmd.id);
                        break;
                }
                break;
            }
            case "UPDATE_CHART": {
                switch (cmd.definition.type) {
                    case "odoo_pie":
                    case "odoo_bar":
                    case "odoo_line": {
                        if (this.shouldChartUpdateReloadDataSource) {
                            this._resetChartDataSource(cmd.id);
                            this.shouldChartUpdateReloadDataSource = false;
                        }
                        this._setChartDataSource(cmd.id);
                        break;
                    }
                }
                break;
            }
            case "ADD_GLOBAL_FILTER":
            case "EDIT_GLOBAL_FILTER":
            case "REMOVE_GLOBAL_FILTER":
            case "SET_GLOBAL_FILTER_VALUE":
            case "CLEAR_GLOBAL_FILTER_VALUE":
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
                    if (!this.getters.getOdooChartIds().includes(cmd.id)) {
                        continue;
                    }
                    const dataSource = this.getChartDataSource(cmd.id);
                    if (
                        dataSource.getInitialDomainString() !==
                        new Domain(cmd.definition.searchParams.domain).toString()
                    ) {
                        this._resetChartDataSource(cmd.id);
                    }
                }
                break;
            }
            case "REFRESH_ODOO_CHART":
                this._refreshOdooChart(cmd.chartId);
                break;
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
        return this.dataSources.get(dataSourceId);
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
            this._addDomain(chartId);
        }
    }

    /**
     * @param {string} chartId
     * @param {string} dataSourceId
     */
    _setupChartDataSource(chartId) {
        const dataSourceId = this._getOdooChartDataSourceId(chartId);
        if (!this.dataSources.contains(dataSourceId)) {
            this._resetChartDataSource(chartId);
        }
        this._setChartDataSource(chartId);
    }

    /**
     * Sets the datasource on the corresponding chart
     * @param {string} chartId
     */
    _resetChartDataSource(chartId) {
        const definition = this.getters.getChart(chartId).getDefinitionForDataSource();
        const dataSourceId = this._getOdooChartDataSourceId(chartId);
        this.dataSources.add(dataSourceId, ChartDataSource, definition);
        this._addDomain(chartId);
    }

    /**
     * Sets the datasource on the corresponding chart
     * @param {string} chartId
     */
    _setChartDataSource(chartId) {
        const chart = this.getters.getChart(chartId);
        chart.setDataSource(this.getChartDataSource(chartId));
    }

    /**
     *
     * @return {Promise[]}
     */
    _getOdooChartsWaitForReady() {
        return this.getters
            .getOdooChartIds()
            .map((chartId) => this.getChartDataSource(chartId).loadMetadata());
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
}

OdooChartUIPlugin.getters = ["getChartDataSource"];
