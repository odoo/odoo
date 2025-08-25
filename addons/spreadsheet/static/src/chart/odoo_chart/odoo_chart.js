import { AbstractChart, CommandResult } from "@odoo/o-spreadsheet";
import { ChartDataSource, chartTypeToDataSourceMode } from "../data_source/chart_data_source";

/**
 * @typedef {import("@web/search/search_model").SearchParams} SearchParams
 *
 * @typedef MetaData
 * @property {Object} domain
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
 * @property {boolean} cumulative
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
        this.metaData = {
            ...definition.metaData,
            mode: chartTypeToDataSourceMode(this.type),
            cumulated: definition.cumulative,
            cumulatedStart: definition.cumulatedStart,
        };
        this.searchParams = definition.searchParams;
        this.legendPosition = definition.legendPosition;
        this.background = definition.background;
        this.dataSource = undefined;
        this.actionXmlId = definition.actionXmlId;
        this.showValues = definition.showValues;
        this._dataSets = definition.dataSets || [];
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
            metaData: this.metaData,
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
            actionXmlId: this.actionXmlId,
            showValues: this.showValues,
            dataSets: this.dataSets,
            datasetsConfig: this.datasetsConfig,
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
    duplicateInDuplicatedSheet() {
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

    get dataSets() {
        if (!this.dataSource) {
            return this.datasetsConfig || [];
        }
        if (!this.dataSource.isReady()) {
            return [];
        }
        const data = this.dataSource.getData();
        return data.datasets.map((ds, index) => this._dataSets?.[index] || {});
    }
}
