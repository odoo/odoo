/** @odoo-module */

import { CommandResult } from "@spreadsheet/o_spreadsheet/cancelled_reason";
import { OdooUIPlugin } from "@spreadsheet/plugins";
import { rpc } from "@web/core/network/rpc";

export class LoggingUIPlugin extends OdooUIPlugin {
    constructor(config) {
        super(config);
    }

    async log(type, datasources) {
        if (rpc && datasources.length) {
            await rpc("/spreadsheet/log", {
                action_type: type,
                datasources,
            });
        }
    }

    allowDispatch(cmd) {
        if (
            cmd.type === "COPY" &&
            this.getters.isReadonly() &&
            this.getLoadedDataSources().length
        ) {
            return CommandResult.Readonly;
        }
        return CommandResult.Success;
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
                    this.log("copy", this.getLoadedDataSources());
                }
                break;
            }
            case "LOG_DATASOURCE_EXPORT": {
                this.log(cmd.action, this.getLoadedDataSources());
                break;
            }
        }
    }

    getLoadedDataSources() {
        const datasources = [];
        datasources.push(
            ...this.getters
                .getOdooChartIds()
                .map((chartId) => this.getters.getChartDataSource(chartId))
                .filter((ds) => ds.isReady())
                .map((ds) => ds.source)
        );
        datasources.push(
            ...this.getters
                .getPivotIds()
                .map((pivotId) => this.getters.getPivot(pivotId))
                .filter((pivot) => pivot.type === "ODOO" && pivot.isValid())
                .map((ds) => ds.source)
        );
        datasources.push(
            ...this.getters
                .getListIds()
                .map((listId) => this.getters.getListDataSource(listId))
                .filter((ds) => ds.isReady())
                .map((ds) => ds.source)
        );
        return datasources;
    }
}

LoggingUIPlugin.getters = ["getLoadedDataSources"];
