import { OdooCorePlugin } from "@spreadsheet/plugins";
import { registerCommand, constants } from "@odoo/o-spreadsheet";
import { CommandResult } from "@spreadsheet/o_spreadsheet/cancelled_reason";
import { deepCopy } from "@web/core/utils/objects";
import { globalFieldMatchingRegistry } from "@spreadsheet/global_filters/helpers";

const { FIGURE_ID_SPLITTER } = constants;

/**
 * @typedef OdooMenuLink
 * @property {"odooMenu"} type
 * @property {number | String} odooMenuId
 */

/**
 * @typedef OdooDataSourceLink
 * @property {"dataSource" } type
 * @property {string} dataSourceType
 * @property {string} dataSourceCoreId
 */

/**
 * @typedef {OdooDataSourceLink | OdooMenuLink} OdooLink
 */

/** Plugin that link charts with Odoo datasources. It contains the datasource type and its id. */
export class ChartOdooLinkPlugin extends OdooCorePlugin {
    static getters = /** @type {const} */ (["getChartOdooLink", "isDataSourceLinkedToChart"]);

    validators = {
        UPDATE_ODOO_LINK_TO_CHART: this.checkOdooLinkToChart,
    };

    handlers = {
        UPDATE_ODOO_LINK_TO_CHART: this.onUpdateOdooLinkToChart,
        DELETE_CHART: this.onDeleteChart,
        DUPLICATE_SHEET: this.onDuplicateSheet,
        REMOVE_PIVOT: this.onRemovePivot,
        REMOVE_ODOO_LIST: this.onRemoveOdooList,
    };

    constructor(config) {
        super(config);
        /** @type {Object.<string, OdooLink | undefined >} */
        this.odooLinkReferences = {};
    }

    checkOdooLinkToChart(cmd) {
        if (cmd.odooLink === undefined || cmd.odooLink.type === "odooMenu") {
            return CommandResult.Success;
        }
        const { dataSourceType, dataSourceCoreId } = cmd.odooLink;
        if (!globalFieldMatchingRegistry.contains(dataSourceType)) {
            return CommandResult.InvalidDataSourceType;
        }
        if (
            !globalFieldMatchingRegistry
                .get(dataSourceType)
                .getIds(this.getters)
                .includes(dataSourceCoreId)
        ) {
            return CommandResult.InvalidDataSourceId;
        }
        return CommandResult.Success;
    }

    onUpdateOdooLinkToChart(cmd) {
        this.history.update("odooLinkReferences", cmd.chartId, deepCopy(cmd.odooLink));
    }

    onDeleteChart(cmd) {
        this.history.update("odooLinkReferences", cmd.chartId, undefined);
        this._removeLinksToDataSource("chart", cmd.chartId);
    }

    onDuplicateSheet(cmd) {
        this.updateOnDuplicateSheet(cmd.sheetId, cmd.sheetIdTo);
    }

    onRemovePivot(cmd) {
        this._removeLinksToDataSource("pivot", cmd.pivotId);
    }

    onRemoveOdooList(cmd) {
        this._removeLinksToDataSource("list", cmd.listId);
    }

    /**
     * Drop the links of every chart pointing to the given data source.
     *
     * @param {string} dataSourceType
     * @param {string} dataSourceCoreId
     */
    _removeLinksToDataSource(dataSourceType, dataSourceCoreId) {
        for (const chartId in this.odooLinkReferences) {
            const { type, ...odooLink } = this.odooLinkReferences[chartId];
            if (
                type === "dataSource" &&
                odooLink.dataSourceType === dataSourceType &&
                odooLink.dataSourceCoreId === dataSourceCoreId
            ) {
                this.history.update("odooLinkReferences", chartId, undefined);
            }
        }
    }

    updateOnDuplicateSheet(sheetIdFrom, sheetIdTo) {
        for (const oldChartId of this.getters.getChartIds(sheetIdFrom)) {
            const link = this.odooLinkReferences[oldChartId];
            if (!link) {
                continue;
            }
            const chartIdBase = oldChartId.split(FIGURE_ID_SPLITTER).pop();
            const newChartId = `${sheetIdTo}${FIGURE_ID_SPLITTER}${chartIdBase}`;
            this.history.update("odooLinkReferences", newChartId, link);
        }
    }

    /**
     * Get Link to the chart, either a datasource or an Odoo menu Id
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
            const { dataSourceCoreId, dataSourceType } = odooLink;
            const datasourceExists = globalFieldMatchingRegistry
                .get(dataSourceType)
                .getIds(this.getters)
                .find((id) => id === dataSourceCoreId);
            return datasourceExists ? odooLink : undefined;
        } else {
            return this.getters.getIrMenu(odooLink.odooMenuId) ? odooLink : undefined;
        }
    }

    isDataSourceLinkedToChart(type, dataSourceCoreId) {
        return Object.values(this.odooLinkReferences).some(
            (ref) =>
                ref &&
                ref.type === "dataSource" &&
                ref.dataSourceType === type &&
                ref.dataSourceCoreId === dataSourceCoreId
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

registerCommand("UPDATE_ODOO_LINK_TO_CHART", { category: "core" });
