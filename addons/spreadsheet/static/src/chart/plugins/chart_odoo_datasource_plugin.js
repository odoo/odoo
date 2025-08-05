import { OdooCorePlugin } from "@spreadsheet/plugins";
import { coreTypes, helpers } from "@odoo/o-spreadsheet";
import { CommandResult } from "@spreadsheet/o_spreadsheet/cancelled_reason";
import { omit } from "@web/core/utils/objects";
import { globalFieldMatchingRegistry } from "@spreadsheet/global_filters/helpers";

const { deepEquals } = helpers;

/**
 * @typedef OdooDataSourceLink
 * @property {string} type
 * @property {string} dataSourceId
 */

/** Plugin that link charts with Odoo datasources. It contains the datasource type and its id. */
export class ChartOdooDatasourcePlugin extends OdooCorePlugin {
    static getters = /** @type {const} */ ([
        "getChartLinkedDataSource",
        "isDataSourceLinkedToChart",
    ]);
    constructor(config) {
        super(config);
        /** @type {Object.<string, OdooDataSourceLink | undefined >} */
        this.odooDatasourceReference = {};
    }

    allowDispatch(cmd) {
        switch (cmd.type) {
            case "LINK_ODOO_DATASOURCE_TO_CHART": {
                if (cmd.odooDataSource === undefined) {
                    return CommandResult.Success;
                }
                const { type, dataSourceId } = cmd.odooDataSource;
                if (!globalFieldMatchingRegistry.contains(type)) {
                    return CommandResult.InvalidDataSourceType;
                }
                if (
                    !globalFieldMatchingRegistry
                        .get(type)
                        .getIds(this.getters)
                        .includes(dataSourceId)
                ) {
                    return CommandResult.InvalidDataSourceId;
                }
                return CommandResult.Success;
            }
            default:
                return CommandResult.Success;
        }
    }

    /**
     * Handle a spreadsheet command
     * @param {Object} cmd Command
     */
    handle(cmd) {
        switch (cmd.type) {
            case "LINK_ODOO_DATASOURCE_TO_CHART":
                this.history.update("odooDatasourceReference", cmd.chartId, cmd.odooDataSource);
                break;
            case "DELETE_CHART":
                this.history.update("odooDatasourceReference", cmd.chartId, undefined);
                for (const chartId in this.odooDatasourceReference) {
                    const { type, dataSourceId } = this.odooDatasourceReference[chartId];
                    if (type === "chart" && dataSourceId === cmd.chartId) {
                        this.history.update("odooDatasourceReference", chartId, undefined);
                    }
                }
                break;
            case "DUPLICATE_SHEET":
                this.updateOnDuplicateSheet(cmd.sheetId, cmd.sheetIdTo);
                break;
            case "REMOVE_PIVOT":
                for (const chartId in this.odooDatasourceReference) {
                    const { type, dataSourceId } = this.odooDatasourceReference[chartId];
                    if (type === "pivot" && dataSourceId === cmd.pivotId) {
                        this.history.update("odooDatasourceReference", chartId, undefined);
                    }
                }
                break;
            case "REMOVE_ODOO_LIST":
                for (const chartId in this.odooDatasourceReference) {
                    const { type, dataSourceId } = this.odooDatasourceReference[chartId];
                    if (type === "list" && dataSourceId === cmd.listId) {
                        this.history.update("odooDatasourceReference", chartId, undefined);
                    }
                }
                break;
        }
    }

    updateOnDuplicateSheet(sheetIdFrom, sheetIdTo) {
        for (const oldChartId of this.getters.getChartIds(sheetIdFrom)) {
            if (!this.odooDatasourceReference[oldChartId]) {
                continue;
            }
            const oldChartDefinition = this.getters.getChartDefinition(oldChartId);
            const oldFigure = this.getters.getFigure(sheetIdFrom, oldChartId);
            const newChartId = this.getters.getChartIds(sheetIdTo).find((newChartId) => {
                const newChartDefinition = this.getters.getChartDefinition(newChartId);
                const newFigure = this.getters.getFigure(sheetIdTo, newChartId);
                return (
                    deepEquals(oldChartDefinition, newChartDefinition) &&
                    deepEquals(omit(newFigure, "id"), omit(oldFigure, "id")) // compare size and position
                );
            });

            if (newChartId) {
                this.history.update(
                    "odooDatasourceReference",
                    newChartId,
                    this.odooDatasourceReference[oldChartId]
                );
            }
        }
    }

    /**
     * Get odoo menu linked to the chart
     *
     * @param {string} chartId
     * @returns {OdooDataSourceLink | undefined}
     */
    getChartLinkedDataSource(chartId) {
        const dataSourceLink = this.odooDatasourceReference[chartId];
        if (!dataSourceLink) {
            return undefined;
        }
        const datasourceExists = globalFieldMatchingRegistry
            .get(dataSourceLink.type)
            .getIds(this.getters)
            .find((id) => id === dataSourceLink.dataSourceId);
        return datasourceExists ? dataSourceLink : undefined;
    }

    isDataSourceLinkedToChart(type, dataSourceId) {
        return Object.values(this.odooDatasourceReference).some(
            (ref) => ref && ref.type === type && ref.dataSourceId === dataSourceId
        );
    }

    import(data) {
        if (data.chartOdooDataSourcesReference) {
            this.odooDatasourceReference = data.chartOdooDataSourcesReference;
        }
    }

    export(data) {
        data.chartOdooDataSourcesReference = this.odooDatasourceReference;
    }
}

coreTypes.add("LINK_ODOO_DATASOURCE_TO_CHART");
