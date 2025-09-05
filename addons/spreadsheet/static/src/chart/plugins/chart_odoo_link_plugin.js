import { OdooCorePlugin } from "@spreadsheet/plugins";
import { coreTypes, helpers } from "@odoo/o-spreadsheet";
import { CommandResult } from "@spreadsheet/o_spreadsheet/cancelled_reason";
import { omit } from "@web/core/utils/objects";
import { globalFieldMatchingRegistry } from "@spreadsheet/global_filters/helpers";

const { deepEquals } = helpers;

/**
 * @typedef OdooDataSourceLink
 * @property {string} dataSourceType
 * @property {string} dataSourceId
 */

/**
 * @typedef OdooMenuLink
 * @property {"odooMenuId"} type
 * @property {number | String} odooMenuId
 */

/**
 * @typedef OdooDataSourceLink
 * @property {"dataSource" } type
 * @property {string} dataSourceType
 * @property {string} dataSourceId
 */

/** Plugin that link charts with Odoo datasources. It contains the datasource type and its id. */
export class ChartOdooLinkPlugin extends OdooCorePlugin {
    static getters = /** @type {const} */ (["getChartOdooLink", "isDataSourceLinkedToChart"]);

    constructor(config) {
        super(config);
        /** @type {Object.<string, OdooDataSourceLink | OdooMenuLink | undefined >} */
        this.odooLinkReferences = {};
    }

    allowDispatch(cmd) {
        switch (cmd.type) {
            case "SET_ODOO_LINK_TO_CHART": {
                if (cmd.odooLink === undefined || cmd.odooLink.type === "odooMenuId") {
                    return CommandResult.Success;
                }
                const { dataSourceType, dataSourceId } = cmd.odooLink;
                if (!globalFieldMatchingRegistry.contains(dataSourceType)) {
                    return CommandResult.InvalidDataSourceType;
                }
                if (
                    !globalFieldMatchingRegistry
                        .get(dataSourceType)
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
            case "SET_ODOO_LINK_TO_CHART":
                if (cmd.odooLink === undefined) {
                    this.history.update("odooLinkReferences", cmd.chartId, undefined);
                } else {
                    this.history.update("odooLinkReferences", cmd.chartId, { ...cmd.odooLink });
                }
                break;
            case "DELETE_CHART":
                this.history.update("odooLinkReferences", cmd.chartId, undefined);
                for (const chartId in this.odooLinkReferences) {
                    const { type, ...odooLink } = this.odooLinkReferences[chartId];
                    if (
                        type === "dataSource" &&
                        odooLink.dataSourceType === "chart" &&
                        odooLink.dataSourceId === cmd.chartId
                    ) {
                        this.history.update("odooLinkReferences", chartId, undefined);
                    }
                }
                break;
            case "DUPLICATE_SHEET":
                this.updateOnDuplicateSheet(cmd.sheetId, cmd.sheetIdTo);
                break;
            case "REMOVE_PIVOT":
                for (const chartId in this.odooLinkReferences) {
                    const { type, ...odooLink } = this.odooLinkReferences[chartId];
                    if (
                        type === "dataSource" &&
                        odooLink.dataSourceType === "pivot" &&
                        odooLink.dataSourceId === cmd.pivotId
                    ) {
                        this.history.update("odooLinkReferences", chartId, undefined);
                    }
                }
                break;
            case "REMOVE_ODOO_LIST":
                for (const chartId in this.odooLinkReferences) {
                    const { type, ...odooLink } = this.odooLinkReferences[chartId];
                    if (
                        type === "dataSource" &&
                        odooLink.dataSourceType === "list" &&
                        odooLink.dataSourceId === cmd.listId
                    ) {
                        this.history.update("odooLinkReferences", chartId, undefined);
                    }
                }
                break;
        }
    }

    updateOnDuplicateSheet(sheetIdFrom, sheetIdTo) {
        for (const oldChartId of this.getters.getChartIds(sheetIdFrom)) {
            if (!this.odooLinkReferences[oldChartId]) {
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
                    "odooLinkReferences",
                    newChartId,
                    this.odooLinkReferences[oldChartId]
                );
            }
        }
    }

    /**
     * Get odoo menu linked to the chart
     *
     * @param {string} chartId
     * @returns {OdooLink | undefined}
     */
    getChartOdooLink(chartId) {
        const odooLink = this.odooLinkReferences[chartId];
        if (!odooLink) {
            return undefined;
        }
        if (odooLink.type === "dataSource") {
            const { dataSourceId, dataSourceType } = odooLink;
            const datasourceExists = globalFieldMatchingRegistry
                .get(dataSourceType)
                .getIds(this.getters)
                .find((id) => id === dataSourceId);
            return datasourceExists ? odooLink : undefined;
        } else {
            return this.getters.getIrMenu(odooLink.odooMenuId) ? odooLink : undefined;
        }
    }

    isDataSourceLinkedToChart(type, dataSourceId) {
        return Object.values(this.odooLinkReferences).some(
            (ref) =>
                ref &&
                ref.type === "dataSource" &&
                ref.dataSourceType === type &&
                ref.dataSourceId === dataSourceId
        );
    }

    import(data) {
        if (data.odooLinkReferences) {
            this.odooLinkReferences = data.odooLinkReferences;
        }
    }

    export(data) {
        data.odooLinkReferences = this.odooLinkReferences;
    }
}

coreTypes.add("SET_ODOO_LINK_TO_CHART");
