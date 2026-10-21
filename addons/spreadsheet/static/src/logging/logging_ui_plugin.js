/** @odoo-module */

import { OdooUIPlugin } from "@spreadsheet/plugins";
import { rpc } from "@web/core/network/rpc";

export class LoggingUIPlugin extends OdooUIPlugin {
    handlers = {
        COPY: this.onCopy,
        LOG_DATASOURCE_EXPORT: this.onLogDatasourceExport,
    };

    async log(type, datasources) {
        if (rpc && datasources.length) {
            await rpc("/spreadsheet/log", {
                action_type: type,
                datasources,
            });
        }
    }

    onCopy() {
        const zones = this.getters.getSelectedZones();
        const size = zones.reduce(
            (acc, zone) => acc + (zone.right - zone.left + 1) * (zone.bottom - zone.top + 1),
            0
        );
        if (size > 400) {
            this.log("copy", this.getLoadedDataSources());
        }
    }

    onLogDatasourceExport(cmd) {
        this.log(cmd.action, this.getLoadedDataSources());
    }

    getLoadedDataSources() {
        const datasources = [];
        datasources.push(
            ...this.getters
                .getOdooChartIds()
                .map((chartId) => this.getters.getChartDataSource(chartId))
                .filter((ds) => ds.isValid())
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
                .filter((ds) => ds.isValid())
                .map((ds) => ds.source)
        );
        return datasources;
    }
}

LoggingUIPlugin.getters = ["getLoadedDataSources"];
