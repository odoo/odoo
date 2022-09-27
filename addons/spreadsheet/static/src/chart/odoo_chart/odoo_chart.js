/** @odoo-module */

import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import GraphDataSource from "../data_source/graph_data_source";

const { AbstractChart, CommandResult } = spreadsheet;

/**
 * @typedef {import("@web/search/search_model").SearchParams} SearchParams
 *
 * @typedef MetaData
 * @property {Array<Object>} domains
 * @property {Array<string>} groupBy
 * @property {string} measure
 * @property {string} mode
 * @property {string} [order]
 * @property {string} resModel
 * @property {boolean} stacked
 *
 * @typedef OdooChartDefinition
 * @property {string} type
 * @property {MetaData} metaData
 * @property {SearchParams} searchParams
 * @property {string} title
 * @property {string} background
 * @property {string} legendPosition
 *
 * @typedef OdooChartDefinitionDataSource
 * @property {MetaData} metaData
 * @property {SearchParams} searchParams
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
        this.metaData = definition.metaData;
        this.searchParams = definition.searchParams;
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
     * @returns {OdooChartDefinitionDataSource}
     */
    getDefinitionForDataSource() {
        return {
            metaData: {
                ...this.metaData,
                mode: this.type.replace("odoo_", ""),
            },
            searchParams: this.searchParams,
        };
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
            metaData: this.metaData,
            searchParams: this.searchParams,
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
        if (dataSource instanceof GraphDataSource) {
            this.dataSource = dataSource;
        }
        else {
            throw new Error("Only GraphDataSources can be added.");
        }
    }
}
