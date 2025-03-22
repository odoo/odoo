/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { OdooViewsDataSource } from "../data_sources/odoo_views_data_source";
import { SpreadsheetPivotModel } from "./pivot_model";
import { omit } from "@web/core/utils/objects";

export default class PivotDataSource extends OdooViewsDataSource {
    /**
     *
     * @override
     * @param {Object} services Services (see DataSource)
     * @param {Object} params
     * @param {import("./pivot_model").PivotMetaData} params.metaData
     * @param {import("./pivot_model").PivotSearchParams} params.searchParams
     */
    constructor(services, params) {
        const filteredParams = {
            ...params,
            searchParams: {
                ...params.searchParams,
                context: omit(
                    params.searchParams.context,
                    "pivot_measures",
                    "pivot_row_groupby",
                    "pivot_column_groupby"
                ),
            },
        };
        super(services, filteredParams);
    }

    async _load() {
        await super._load();
        /** @type {SpreadsheetPivotModel} */
        this._model = new SpreadsheetPivotModel(
            { _t },
            {
                metaData: this._metaData,
                searchParams: this._searchParams,
            },
            {
                orm: this._orm,
                metadataRepository: this._metadataRepository,
            }
        );
        await this._model.load(this._searchParams);
    }

    async copyModelWithOriginalDomain() {
        await this.loadMetadata();
        const model = new SpreadsheetPivotModel(
            { _t },
            {
                metaData: this._metaData,
                searchParams: this._initialSearchParams,
            },
            {
                orm: this._orm,
                metadataRepository: this._metadataRepository,
            }
        );
        await model.load(this._initialSearchParams);
        return model;
    }

    getReportMeasures() {
        this._assertDataIsLoaded();
        return this._model.getReportMeasures();
    }

    /**
     * @param {string[]} domain
     */
    getDisplayedPivotHeaderValue(domain) {
        this._assertDataIsLoaded();
        return this._model.getDisplayedPivotHeaderValue(domain);
    }

    /**
     * @param {string[]} domain
     */
    getPivotHeaderValue(domain) {
        this._assertDataIsLoaded();
        return this._model.getPivotHeaderValue(domain);
    }

    /**
     * @param {string} measure Field name of the measures
     * @param {string[]} domain
     */
    markAsValueUsed(measure, domain) {
        if (this._model) {
            this._model.markAsValueUsed(measure, domain);
        }
    }

    /**
     * @param {string[]} domain
     */
    markAsHeaderUsed(domain) {
        if (this._model) {
            this._model.markAsHeaderUsed(domain);
        }
    }

    /**
     * @param {string} measure Field name of the measures
     * @param {string[]} domain
     * @returns {boolean}
     */
    isUsedValue(measure, domain) {
        this._assertDataIsLoaded();
        return this._model.isUsedValue(measure, domain);
    }

    /**
     * @param {string[]} domain
     * @returns {boolean}
     */
    isUsedHeader(domain) {
        this._assertDataIsLoaded();
        return this._model.isUsedHeader(domain);
    }

    clearUsedValues() {
        if (this._model) {
            this._model.clearUsedValues();
        }
    }

    getTableStructure() {
        this._assertDataIsLoaded();
        return this._model.getTableStructure();
    }

    /**
     * @param {string} measure Field name of the measures
     * @param {string[]} domain
     */
    getPivotCellValue(measure, domain) {
        this._assertDataIsLoaded();
        return this._model.getPivotCellValue(measure, domain);
    }

    /**
     * @param {string[]}
     */
    getPivotCellDomain(domain) {
        this._assertDataIsLoaded();
        return this._model.getPivotCellDomain(domain);
    }

    /**
     * @param {string} fieldName
     * @param {string} value raw string value
     * @returns {string}
     */
    getGroupByDisplayLabel(fieldName, value) {
        this._assertDataIsLoaded();
        return this._model.getGroupByDisplayLabel(fieldName, value);
    }

    /**
     * @param {string} fieldName
     * @returns {string}
     */
    getFormattedGroupBy(fieldName) {
        this._assertDataIsLoaded();
        return this._model.getFormattedGroupBy(fieldName);
    }

    /**
     * @param {string} groupFieldString
     */
    parseGroupField(groupFieldString) {
        this._assertDataIsLoaded();
        return this._model.parseGroupField(groupFieldString);
    }

    /**
     * @param {"COLUMN" | "ROW"} dimension
     * @returns {boolean}
     */
    isGroupedOnlyByOneDate(dimension) {
        this._assertDataIsLoaded();
        return this._model.isGroupedOnlyByOneDate(dimension);
    }

    /**
     * @param {"COLUMN" | "ROW"} dimension
     * @returns {string}
     */
    getGroupOfFirstDate(dimension) {
        this._assertDataIsLoaded();
        return this._model.getGroupOfFirstDate(dimension);
    }

    /**
     * @param {"COLUMN" | "ROW"} dimension
     * @param {number} index
     * @returns {string}
     */
    getGroupByAtIndex(dimension, index) {
        this._assertDataIsLoaded();
        return this._model.getGroupByAtIndex(dimension, index);
    }

    /**
     * @param {string} fieldName
     * @returns {boolean}
     */
    isColumnGroupBy(fieldName) {
        this._assertDataIsLoaded();
        return this._model.isColumnGroupBy(fieldName);
    }

    /**
     * @param {string} fieldName
     * @returns {boolean}
     */
    isRowGroupBy(fieldName) {
        this._assertDataIsLoaded();
        return this._model.isRowGroupBy(fieldName);
    }

    /**
     * @returns {number}
     */
    getNumberOfColGroupBys() {
        this._assertDataIsLoaded();
        return this._model.getNumberOfColGroupBys();
    }

    async prepareForTemplateGeneration() {
        this._assertDataIsLoaded();
        await this._model.prepareForTemplateGeneration();
    }
}
