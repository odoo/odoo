/** @odoo-module */

import * as spreadsheet from "@odoo/o-spreadsheet";
import { Domain } from "@web/core/domain";
import { globalFiltersFieldMatchers } from "@spreadsheet/global_filters/plugins/global_filters_core_plugin";
import ChartDataSource from "../data_source/chart_data_source";
import { sprintf } from "@web/core/utils/strings";
import { _t } from "@web/core/l10n/translation";

const { UIPlugin } = spreadsheet;

export default class OdooChartUIPlugin extends UIPlugin {
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
                    case "odoo_line":
                        this._setChartDataSource(cmd.id);
                        break;
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
            case "REDO":
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
        this.getters.getChartDataSource(chartId).addDomain(domain);
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
        const definition = this.getters.getChart(chartId).getDefinitionForDataSource();
        if (!this.dataSources.contains(dataSourceId)) {
            this.dataSources.add(dataSourceId, ChartDataSource, definition);
        }
        this._setChartDataSource(chartId);
    }

    /**
     * Sets the catasource on the corresponding chart
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
}

OdooChartUIPlugin.getters = ["getChartDataSource"];
