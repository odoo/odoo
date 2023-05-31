/** @odoo-module */

import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import ChartDataSource from "../data_source/chart_data_source";

const { AbstractChart, CommandResult } = spreadsheet;

/**
 *
 * @typedef ChartDataSourceDefinition
 * @property {string} id
 * @property {string} model
 * @property {Array<Object>} domain
 * @property {Object} context
 * @property {Array<string>} groupBy
 * @property {string} measure
 * @property {object} [orderBy]
 *
 * @typedef OdooChartDefinition
 * @property {string} type
 * @property {ChartDataSourceDefinition} dataSourceDefinition
 * @property {string} title
 * @property {string} background
 * @property {string} legendPosition
 *
 */

export class OdooChart extends AbstractChart {
    /**
     * @param {OdooChartDefinition} definition
     * @param {string} sheetId
     * @param {Object} getters
     */
    constructor(definition, sheetId, getters) {
        super(definition, sheetId, getters);
        this.type = definition.type;
        this.dataSourceDefinition = {
            ...definition.dataSourceDefinition,
            mode: this.type.replace("odoo_", ""),
        };
        this.legendPosition = definition.legendPosition;
        this.background = definition.background;
        this.dataSource = undefined;
    }

    static transformDefinition(definition) {
        return definition;
    }

    static validateChartDefinition(validator, definition) {
        return CommandResult.Success;
    }

    static getDefinitionFromContextCreation() {
        throw new Error("It's not possible to convert an Odoo chart to a native chart");
    }

    /**
     * @returns {OdooChartDefinition}
     */
    getDefinition() {
        return {
            //@ts-ignore Defined in the parent class
            title: this.title,
            background: this.background,
            legendPosition: this.legendPosition,
            dataSourceDefinition: this.dataSourceDefinition,
            type: this.type,
        };
    }

    getDefinitionForExcel() {
        // Export not supported
        return undefined;
    }

    /**
     * @returns {OdooChart}
     */
    updateRanges() {
        // No range on this graph
        return this;
    }

    /**
     * @returns {OdooChart}
     */
    copyForSheetId() {
        return this;
    }

    /**
     * @returns {OdooChart}
     */
    copyInSheetId() {
        return this;
    }

    getContextCreation() {
        return {};
    }

    getSheetIdsUsedInChartRanges() {
        return [];
    }

    setDataSource(dataSource) {
        if (dataSource instanceof ChartDataSource) {
            this.dataSource = dataSource;
        } else {
            throw new Error("Only ChartDataSources can be added.");
        }
    }
}
