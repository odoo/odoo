/** @odoo-module */

import { Domain } from "@web/core/domain";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { OdooViewsDataSource } from "../data_sources/odoo_views_data_source";
import { SpreadsheetPivotModel } from "./pivot_model";
import { EvaluationError } from "@odoo/o-spreadsheet";

export class PivotDataSource extends OdooViewsDataSource {
    /**
     *
     * @override
     * @param {Object} services Services (see DataSource)
     * @param {import("@spreadsheet").PivotRuntime} params
     */
    constructor(services, params) {
        super(services, params);
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

        const domain = new Domain(this._initialSearchParams.domain).toList({
            ...this._initialSearchParams.context,
            ...user.context,
        });

        const searchParams = { ...this._initialSearchParams, domain };
        await model.load(searchParams);
        return model;
    }

    /**
     * High level method computing the result of ODOO.PIVOT.HEADER functions.
     * - regular function 'ODOO.PIVOT.HEADER(1,"stage_id",2,"user_id",6)'
     * - measure header 'ODOO.PIVOT.HEADER(1,"stage_id",2,"user_id",6,"measure","expected_revenue")
     * - positional header 'ODOO.PIVOT.HEADER(1,"#stage_id",1,"#user_id",1)'
     *
     * @param {(string | number)[]} domainArgs arguments of the function (except the first one which is the pivot id)
     * @returns {string | number}
     */
    computeOdooPivotHeaderValue(domainArgs) {
        this._assertDataIsLoaded();
        if (domainArgs.length === 0) {
            return _t("Total");
        }
        if (domainArgs.at(-2) === "measure") {
            return this.getMeasureDisplayName(domainArgs.at(-1));
        }
        return this._model.getGroupByCellValue(
            domainArgs.at(-2),
            this._model.getLastPivotGroupValue(domainArgs)
        );
    }

    /**
     * @param {string} measure
     * @returns {string}
     */
    getMeasureDisplayName(measure) {
        if (measure === "__count") {
            return _t("Count");
        }
        const field = this.getField(measure);
        if (field === undefined) {
            throw new EvaluationError(_t("Field %s does not exist", measure));
        }
        return field.string;
    }

    /**
     * @param {(string | number)[]} domainArgs
     */
    getLastPivotGroupValue(domainArgs) {
        this._assertDataIsLoaded();
        return this._model.getLastPivotGroupValue(domainArgs);
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

    async prepareForTemplateGeneration() {
        this._assertDataIsLoaded();
        await this._model.prepareForTemplateGeneration();
    }
}
