/** @odoo-module */

import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";

export class LoggingUIPlugin extends spreadsheet.UIPlugin {
    constructor(getters, history, dispatch, config) {
        super(getters, history, dispatch, config);
        if ("env" in config.evalContext) {
            this.rpc = config.evalContext.env.services.rpc;
        }
    }

    log(type, datasources) {
        if (this.rpc && datasources.length) {
            this.rpc("/spreadsheet/log", {
                type,
                datasources,
            });
        }
    }

    /**
     * Handle a spreadsheet command
     * @param {Object} cmd Command
     */
    handle(cmd) {
        switch (cmd.type) {
            case "COPY": {
                const zones = this.getters.getSelectedZones();
                const size = zones.reduce(
                    (acc, zone) =>
                        acc + (zone.right - zone.left + 1) * (zone.bottom - zone.top + 1),
                    0
                );
                if (size > 400) {
                    this.dispatch("LOG_DATASOURCE_EXPORT", { action: "copy" });
                }
                break;
            }
            case "LOG_DATASOURCE_EXPORT": {
                this.log(cmd.action, this.getLoadedDataSources());
                break;
            }
        }
    }

    getDatasources() {
        const datasources = [];
        datasources.push(
            ...this.getters
                .getOdooChartIds()
                .map((chartId) => this.getters.getChartDataSource(chartId))
        );
        datasources.push(
            ...this.getters.getPivotIds().map((pivotId) => this.getters.getPivotDataSource(pivotId))
        );
        datasources.push(
            ...this.getters.getListIds().map((listId) => this.getters.getListDataSource(listId))
        );
        return datasources;
    }

    getLoadedDataSources() {
        return this.getDatasources()
            .filter((ds) => ds._isFullyLoaded)
            .map((ds) => ds.source);
    }
}

LoggingUIPlugin.getters = ["getDatasources", "getLoadedDataSources"];
