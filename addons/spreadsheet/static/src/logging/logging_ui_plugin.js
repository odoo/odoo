/** @odoo-module */

import { CommandResult } from "@spreadsheet/o_spreadsheet/cancelled_reason";
import { OdooUIPlugin } from "@spreadsheet/plugins";
import { rpc } from "@web/core/network/rpc";
import * as spreadsheet from "@odoo/o-spreadsheet";
const { cellMenuRegistry, topbarMenuRegistry, colMenuRegistry, rowMenuRegistry } =
    spreadsheet.registries;

cellMenuRegistry.get("copy").isEnabled = (env) => !env.isFrozenSpreadsheet?.();

colMenuRegistry.get("copy").isEnabled = (env) => !env.isFrozenSpreadsheet?.();

rowMenuRegistry.get("copy").isEnabled = (env) => !env.isFrozenSpreadsheet?.();

topbarMenuRegistry.get("edit").children.filter((c) => c.id === "copy")[0].isEnabled = (env) =>
    !env.isFrozenSpreadsheet?.();

export class LoggingUIPlugin extends OdooUIPlugin {
    validators = {
        COPY: this.checkCopyIsAllowed,
    };

    handlers = {
        COPY: this.onCopy,
        LOG_DATASOURCE_EXPORT: this.onLogDatasourceExport,
    };

    constructor(config) {
        super(config);
        this.isFrozenSpreadsheet = config.custom.isFrozenSpreadsheet;
    }

    async log(type, datasources) {
        if (rpc && datasources.length) {
            await rpc("/spreadsheet/log", {
                action_type: type,
                datasources,
            });
        }
    }

    checkCopyIsAllowed() {
        if (this.isFrozenSpreadsheet) {
            return CommandResult.Readonly;
        }
        return CommandResult.Success;
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
