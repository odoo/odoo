/** @odoo-module */

import spreadsheet from "../../o_spreadsheet/o_spreadsheet_extended";
import GraphDataSource from "../data_source/graph_data_source";

const { CorePlugin } = spreadsheet;
const { corePluginRegistry } = spreadsheet.registries;

/**
 * @typedef {import("@web/views/graph/graph_model").GraphModel} GraphModel
 */

export default class OdooGraphPlugin extends CorePlugin {
    constructor(getters, history, range, dispatch, config, uuidGenerator) {
        super(getters, history, range, dispatch, config, uuidGenerator);
        this.dataSources = config.dataSources;

        /** @type {Object.<string, string>} */
        this.graphsDataSources = {};
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
                        this._addGraphDataSource(cmd.id, cmd.definition.dataSourceId);
                        break;
                }
                break;
            }
            case "ADD_GRAPH_DOMAIN":
                this.getters.getGraphDataSource(cmd.id).addDomain(cmd.domain);
        }
    }

    // -------------------------------------------------------------------------
    // Getters
    // -------------------------------------------------------------------------

    /**
     * Get all the odoo chart ids
     * @returns {Array<string>}
     */
    getOdooChartIds() {
        const ids = [];
        for (const sheetId of this.getters.getSheetIds()) {
            ids.push(
                ...this.getters
                    .getChartIds(sheetId)
                    .filter((id) => this.getters.getChartType(id).startsWith("odoo_"))
            );
        }
        return ids;
    }

    /**
     * @param {string} id
     * @returns {GraphDataSource|undefined}
     */
    getGraphDataSource(id) {
        const dataSourceId = this.graphsDataSources[id];
        return this.dataSources.get(dataSourceId);
    }

    import(data) {
        for (const sheet of data.sheets) {
            if (sheet.figures) {
                for (const figure of sheet.figures) {
                    if (figure.tag === "chart" && figure.data.type.startsWith("odoo_")) {
                        this._addGraphDataSource(figure.id, this.uuidGenerator.uuidv4());
                    }
                }
            }
        }
    }

    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------

    /**
     * @param {string} id
     * @param {string} dataSourceId
     */
    _addGraphDataSource(id, dataSourceId) {
        const graphsDataSources = { ...this.graphsDataSources };
        graphsDataSources[id] = dataSourceId;
        const definition = this.getters.getChart(id).getDefinitionForDataSource();
        if (!this.dataSources.contains(dataSourceId)) {
            this.dataSources.add(dataSourceId, GraphDataSource, definition);
        }
        this.history.update("graphsDataSources", graphsDataSources);
    }
}

OdooGraphPlugin.getters = ["getGraphDataSource", "getOdooChartIds"];

corePluginRegistry.add("odoo_graph_plugin", OdooGraphPlugin);
