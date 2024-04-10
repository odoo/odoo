//@ts-check

import { Domain } from "@web/core/domain";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { OdooViewsDataSource } from "../data_sources/odoo_views_data_source";
import { OdooPivotModel } from "./pivot_model";
import { EvaluationError, PivotRuntimeDefinition, registries, helpers } from "@odoo/o-spreadsheet";
import { LOADING_ERROR } from "@spreadsheet/data_sources/data_source";

const { pivotRegistry, supportedPivotExplodedFormulaRegistry } = registries;
const { pivotTimeAdapter } = helpers;

/**
 * @typedef {import("@odoo/o-spreadsheet").FPayload} FPayload
 * @typedef {import("@odoo/o-spreadsheet").PivotMeasure} PivotMeasure
 * @typedef {import("@spreadsheet").WebPivotModelParams} WebPivotModelParams
 * @typedef {import("@spreadsheet").OdooPivot<OdooPivotRuntimeDefinition>} IPivot
 * @typedef {import("@spreadsheet").OdooFields} OdooFields
 * @typedef {import("@spreadsheet").OdooPivotCoreDefinition} OdooPivotCoreDefinition
 * @typedef {import("@spreadsheet").SortedColumn} SortedColumn
 * @typedef {import("@spreadsheet").OdooGetters} OdooGetters
 */

/**
 * @implements {IPivot}
 */
export class OdooPivot extends OdooViewsDataSource {
    /**
     *
     * @override
     * @param {Object} services Services (see DataSource)
     * @param {Object} params
     * @param {OdooPivotCoreDefinition} params.definition
     * @param {OdooGetters} params.getters
     */
    constructor(services, { definition, getters }) {
        const params = {
            metaData: {
                resModel: definition.model,
            },
            searchParams: {
                domain: definition.domain,
                context: definition.context,
            },
        };
        super(services, params);
        /** @type {"ODOO"} */
        this.type = "ODOO";
        this._rawDefinition = definition;
        /** @type {OdooPivotRuntimeDefinition | undefined} */
        this._runtimeDefinition = undefined;
        /** @type {OdooPivotModel | undefined} */
        this._model = undefined;
        /** @type {OdooGetters} */
        this.getters = getters;
        this.needsReevaluation = false;
        this.setup();
    }

    setup() {}

    init(params) {
        this.load(params);
    }

    async _load() {
        await super._load();
        this._runtimeDefinition = new OdooPivotRuntimeDefinition(
            this._rawDefinition,
            this._metaData.fields
        );
        this._model = new OdooPivotModel(
            { _t },
            {
                //@ts-ignore this._metaData.fields is loaded at this point
                metaData: this._metaData,
                definition: this._runtimeDefinition,
                searchParams: this._searchParams,
            },
            {
                orm: this._orm,
                serverData: this.odooDataProvider.serverData,
            }
        );
        await this._model.load(this._searchParams);
    }

    get definition() {
        if (!this._runtimeDefinition) {
            throw LOADING_ERROR;
        }
        return this._runtimeDefinition;
    }

    /**
     * High level method computing the result of PIVOT.HEADER functions.
     * - regular function 'PIVOT.HEADER(1,"stage_id",2,"user_id",6)'
     * - measure header 'PIVOT.HEADER(1,"stage_id",2,"user_id",6,"measure","expected_revenue")
     * - positional header 'PIVOT.HEADER(1,"#stage_id",1,"#user_id",1)'
     *
     * @param {string[]} domainArgs arguments of the function (except the first one which is the pivot id)
     * @returns {FPayload}
     */
    getPivotHeaderValueAndFormat(domainArgs) {
        this.assertIsValid();
        if (domainArgs.length === 0) {
            return { value: _t("Total") };
        }
        if (domainArgs.at(-2) === "measure") {
            const measureName = domainArgs.at(-1).toString();
            return { value: this.getMeasure(measureName).displayName };
        }
        const field = domainArgs.at(-2).toString();
        const value = this._model.getGroupByCellValue(
            field,
            this._model.getLastPivotGroupValue(domainArgs)
        );
        const format = this._getPivotFieldFormat(field);
        return { value, format };
    }

    /**
     * Get the measure object from its name
     *
     * @param {string} name
     * @returns {PivotMeasure}
     */
    getMeasure(name) {
        const measures = this.definition.measures;
        const measure = measures.find((m) => m.name === name);
        if (!measure) {
            throw new EvaluationError(_t("Field %s does not exist", name));
        }
        return measure;
    }

    /**
     * @param {Array<string | number>} domainArgs
     * @returns {string | number | boolean}
     */
    getLastPivotGroupValue(domainArgs) {
        this.assertIsValid();
        return this._model.getLastPivotGroupValue(domainArgs);
    }

    getTableStructure() {
        this.assertIsValid();
        return this._model.getTableStructure();
    }

    /**
     * Get the format associated to a pivot field (based on its type)
     * e.g. integer => 0, float => #,##0.00, monetary => #,##0.00
     *
     * @param {string} fieldName
     * @returns {string | undefined}
     */
    _getPivotFieldFormat(fieldName) {
        const { field, granularity } = this.parseGroupField(fieldName);
        switch (field.type) {
            case "integer":
                return "0";
            case "float":
                return "#,##0.00";
            case "monetary":
                return this.getters.getCompanyCurrencyFormat() || "#,##0.00";
            case "date":
            case "datetime": {
                const timeAdapter = pivotTimeAdapter(granularity);
                return timeAdapter.getFormat(this.getters.getLocale());
            }
            default:
                return undefined;
        }
    }

    /**
     * @param {string} measureName
     * @param {string[]} domain
     * @returns {FPayload}
     */
    getPivotCellValueAndFormat(measureName, domain) {
        this.assertIsValid();
        const value = this._model.getPivotCellValue(measureName, domain);
        const measure = this.getMeasure(measureName);
        let format;
        switch (measure.aggregator) {
            case "count":
            case "count_distinct":
                format = "0";
                break;
            default:
                format = measure.name === "__count" ? "0" : this._getPivotFieldFormat(measure.name);
        }
        return { value, format };
    }

    //--------------------------------------------------------------------------
    // Odoo specific
    //--------------------------------------------------------------------------

    /**
     * @param {string} groupFieldString
     */
    parseGroupField(groupFieldString) {
        this.assertIsValid();
        return this._model.parseGroupField(groupFieldString);
    }

    /**
     * @param {string[]} domain
     */
    getPivotCellDomain(domain) {
        this.assertIsValid();
        return this._model.getPivotCellDomain(domain);
    }

    /**
     * @param {string} fieldName
     * @returns {{ value: string | number | boolean, label: string }[]}
     */
    getPossibleFieldValues(fieldName) {
        this.assertIsValid();
        return this._model.getPossibleFieldValues(fieldName);
    }

    async copyModelWithOriginalDomain() {
        await this.loadMetadata();
        this._runtimeDefinition = new OdooPivotRuntimeDefinition(
            this._rawDefinition,
            this._metaData.fields
        );
        const model = new OdooPivotModel(
            { _t },
            {
                //@ts-ignore this._metaData.fields is loaded at this point
                metaData: this._metaData,
                definition: this._runtimeDefinition,
                searchParams: this._initialSearchParams,
            },
            { orm: this._orm }
        );

        const domain = new Domain(this._initialSearchParams.domain).toList({
            ...this._initialSearchParams.context,
            ...user.context,
        });

        const searchParams = { ...this._initialSearchParams, domain };
        await model.load(searchParams);
        return model;
    }
}

export class OdooPivotRuntimeDefinition extends PivotRuntimeDefinition {
    /**
     * @param {OdooPivotCoreDefinition} definition
     * @param {OdooFields} fields
     */
    constructor(definition, fields) {
        super(definition, fields);
        /** @type {Domain} */
        this._domain = new Domain(definition.domain);
        /** @type {Object} */
        this._context = definition.context;
        /** @type {string} */
        this._model = definition.model;
        /** @type {SortedColumn} */
        this._sortedColumn = definition.sortedColumn;
        /**
         * month_number is currently not supported in Odoo, remove it
         */
        for (const dimension of this.columns.concat(this.rows)) {
            if (dimension.granularity === "month_number") {
                dimension.granularity = undefined;
                dimension.nameWithGranularity = dimension.name;
            }
        }
    }

    get sortedColumn() {
        return this._sortedColumn;
    }

    get domain() {
        return this._domain;
    }

    get context() {
        return this._context;
    }

    get model() {
        return this._model;
    }

    /**
     * Only for Web pivot model compatibility
     * @param {OdooFields} [fields]
     *
     * @returns {WebPivotModelParams}
     */

    getDefinitionForPivotModel(fields) {
        return {
            searchParams: {
                domain: this.domain,
                context: this.context,
                groupBy: [],
                orderBy: [],
            },
            metaData: {
                sortedColumn: this.sortedColumn,
                activeMeasures: this.measures.map((m) => m.name),
                resModel: this.model,
                colGroupBys: this.columns.map((c) => c.nameWithGranularity),
                rowGroupBys: this.rows.map((r) => r.nameWithGranularity),
                fieldAttrs: {},
                fields,
            },
        };
    }
}

const MEASURES_TYPES = ["integer", "float", "monetary"];

pivotRegistry.add("ODOO", {
    ui: OdooPivot,
    definition: OdooPivotRuntimeDefinition,
    externalData: true,
    onIterationEndEvaluation: () => {},
    granularities: ["year", "quarter", "month", "week", "day"],
    isMeasureCandidate: (field) =>
        ((MEASURES_TYPES.includes(field.type) && field.aggregator) || field.type === "many2one") &&
        field.name !== "id" &&
        field.store,
    isGroupable: (field) => field.groupable,
});

supportedPivotExplodedFormulaRegistry.add("ODOO", true);
