import { OdooCorePlugin } from "@spreadsheet/plugins";
import { coreTypes, evaluationCommandTypes, constants, corePlugins } from "@odoo/o-spreadsheet";
import { IrMenuPlugin } from "../../ir_ui_menu/ir_ui_menu_plugin";
import { CommandResult } from "@spreadsheet/o_spreadsheet/cancelled_reason";
import { deepCopy } from "@web/core/utils/objects";
import { ListCorePlugin } from "@spreadsheet/list";
import { OdooChartCorePlugin } from "./odoo_chart_core_plugin";
import { ListCoreGlobalFilterPlugin } from "../../list/plugins/list_core_global_filter_plugin";
import { PivotCoreGlobalFilterPlugin } from "../../pivot/plugins/pivot_core_global_filter_plugin";

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
    static dependencies = [
        IrMenuPlugin,
        ListCorePlugin,
        corePlugins.PivotCorePlugin,
        PivotCoreGlobalFilterPlugin,
        OdooChartCorePlugin,
        ListCoreGlobalFilterPlugin,
    ];
    static getters = /** @type {const} */ (["getChartOdooLink", "isDataSourceLinkedToChart"]);

    constructor(config) {
        super(config);
        /** @type {Object.<string, OdooLink | undefined >} */
        this.odooLinkReferences = {};
        this.globalFieldMatchingRegistry = this.getters.getGlobalFieldMatchingRegistry();
    }

    allowDispatch(cmd) {
        switch (cmd.type) {
            case "UPDATE_ODOO_LINK_TO_CHART": {
                if (cmd.odooLink === undefined || cmd.odooLink.type === "odooMenu") {
                    return CommandResult.Success;
                }
                const { dataSourceType, dataSourceCoreId } = cmd.odooLink;
                if (!this.globalFieldMatchingRegistry.contains(dataSourceType)) {
                    return CommandResult.InvalidDataSourceType;
                }
                if (
                    !this.globalFieldMatchingRegistry
                        .get(dataSourceType)
                        .getIds()
                        .includes(dataSourceCoreId)
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
            case "UPDATE_ODOO_LINK_TO_CHART":
                this.history.update("odooLinkReferences", cmd.chartId, deepCopy(cmd.odooLink));
                break;
            case "DELETE_CHART":
                this.history.update("odooLinkReferences", cmd.chartId, undefined);
                for (const chartId in this.odooLinkReferences) {
                    const { type, ...odooLink } = this.odooLinkReferences[chartId];
                    if (
                        type === "dataSource" &&
                        odooLink.dataSourceType === "chart" &&
                        odooLink.dataSourceCoreId === cmd.chartId
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
                        odooLink.dataSourceCoreId === cmd.pivotId
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
                        odooLink.dataSourceCoreId === cmd.listId
                    ) {
                        this.history.update("odooLinkReferences", chartId, undefined);
                    }
                }
                break;
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
            const datasourceExists = this.globalFieldMatchingRegistry
                .get(dataSourceType)
                .getIds()
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

coreTypes.add("UPDATE_ODOO_LINK_TO_CHART");

// `evaluationCommandTypes` is a snapshot of `coreTypes` taken when o-spreadsheet
// is loaded, so every core type added here has to be registered again for
// evaluation plugins to receive it.
// TODO: remove once `isEvaluationCommand` also checks `coreTypes` at call time.
evaluationCommandTypes.add("UPDATE_ODOO_LINK_TO_CHART");
