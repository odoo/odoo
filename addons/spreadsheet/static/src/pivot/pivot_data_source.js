/** @odoo-module */

import { Domain } from "@web/core/domain";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { OdooViewsDataSource } from "../data_sources/odoo_views_data_source";
import { SpreadsheetPivotModel } from "./pivot_model";
import { Loadable } from "../data_sources/loadable";

export class PivotDataSource extends OdooViewsDataSource {
    /**
     *
     * @override
     * @param {Object} services Services (see DataSource)
     * @param {Object} params
     * @param {import("./pivot_model").PivotMetaData} params.metaData
     * @param {import("./pivot_model").PivotSearchParams} params.searchParams
     */
    constructor(services, params) {
        super(services, params);
        /** @type {() => Loadable<SpreadsheetPivotModel>} */
        this._model = lazy(() => new Loadable(this.load()));
    }

    async _load() {
        await super._load();
        /** @type {SpreadsheetPivotModel} */
        const model = new SpreadsheetPivotModel(
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
        await model.load(this._searchParams);
        return model;
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

        const domain = new Domain(this._initialSearchParams.domain).toList({
            ...this._initialSearchParams.context,
            ...user.context,
        });

        const searchParams = { ...this._initialSearchParams, domain };
        await model.load(searchParams);
        return model;
    }

    /**
     * @param {string[]} domain
     */
    getDisplayedPivotHeaderValue(domain) {
        return this._model().map((model) => model.getDisplayedPivotHeaderValue(domain));
    }

    /**
     * @param {string[]} domain
     */
    getPivotHeaderValue(domain) {
        return this._model().map((model) => model.getPivotHeaderValue(domain));
    }

    /**
     * @param {string} measure Field name of the measures
     * @param {string[]} domain
     */
    markAsValueUsed(measure, domain) {
        if (this._model().status === Loadable.resolved) {
            this._model().value.markAsValueUsed(measure, domain);
        }
    }

    /**
     * @param {string[]} domain
     */
    markAsHeaderUsed(domain) {
        if (this._model().status === Loadable.resolved) {
            this._model().value.markAsHeaderUsed(domain);
        }
    }

    /**
     * @param {string} measure Field name of the measures
     * @param {string[]} domain
     * @returns {boolean}
     */
    isUsedValue(measure, domain) {
        return this._model().map((model) => model.isUsedValue(measure, domain));
    }

    /**
     * @param {string[]} domain
     * @returns {boolean}
     */
    isUsedHeader(domain) {
        return this._model().map((model) => model.isUsedHeader(domain));
    }

    clearUsedValues() {
        if (this._model().status === Loadable.resolved) {
            this._model().value.clearUsedValues();
        }
    }

    getTableStructure() {
        return this._model().map((model) => model.getTableStructure());
    }

    /**
     * @param {string} measure Field name of the measures
     * @param {string[]} domain
     */
    getPivotCellValue(measure, domain) {
        return this._model().map((model) => model.getPivotCellValue(measure, domain));
    }

    /**
     * @param {string[]}
     */
    getPivotCellDomain(domain) {
        return this._model().map((model) => model.getPivotCellDomain(domain));
    }

    /**
     * @param {string} fieldName
     * @param {string} value raw string value
     * @param {object} locale
     * @returns {string}
     */
    getGroupByDisplayLabel(fieldName, value, locale) {
        return this._model().map((model) => model.getGroupByDisplayLabel(fieldName, value, locale));
    }

    /**
     * @param {string} fieldName
     * @returns {string}
     */
    getFormattedGroupBy(fieldName) {
        return this._model().map((model) => model.getFormattedGroupBy(fieldName));
    }

    /**
     * @param {string} groupFieldString
     */
    parseGroupField(groupFieldString) {
        return this._model().map((model) => model.parseGroupField(groupFieldString));
    }

    /**
     * @param {"COLUMN" | "ROW"} dimension
     * @returns {boolean}
     */
    isGroupedOnlyByOneDate(dimension) {
        return this._model().map((model) => model.isGroupedOnlyByOneDate(dimension));
    }

    /**
     * @param {"COLUMN" | "ROW"} dimension
     * @returns {string}
     */
    getGroupOfFirstDate(dimension) {
        return this._model().map((model) => model.getGroupOfFirstDate(dimension));
    }

    /**
     * @param {"COLUMN" | "ROW"} dimension
     * @param {number} index
     * @returns {string}
     */
    getGroupByAtIndex(dimension, index) {
        return this._model().map((model) => model.getGroupByAtIndex(dimension, index));
    }

    /**
     * @param {string} fieldName
     * @returns {boolean}
     */
    isColumnGroupBy(fieldName) {
        return this._model().map((model) => model.isColumnGroupBy(fieldName));
    }

    /**
     * @param {string} fieldName
     * @returns {boolean}
     */
    isRowGroupBy(fieldName) {
        return this._model().map((model) => model.isRowGroupBy(fieldName));
    }

    /**
     * @returns {number}
     */
    getNumberOfColGroupBys() {
        return this._model().map((model) => model.getNumberOfColGroupBys());
    }

    async prepareForTemplateGeneration() {
        return this._model().map((model) => model.prepareForTemplateGeneration()).promise;
    }
}
