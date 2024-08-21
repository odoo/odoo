//@ts-check

import { Domain } from "@web/core/domain";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { omit } from "@web/core/utils/objects";
import { OdooViewsDataSource } from "../data_sources/odoo_views_data_source";
import { NO_RECORD_AT_THIS_POSITION, OdooPivotModel } from "./pivot_model";
import { EvaluationError, PivotRuntimeDefinition, registries, helpers } from "@odoo/o-spreadsheet";
import { LOADING_ERROR } from "@spreadsheet/data_sources/data_source";

const { pivotRegistry, supportedPivotPositionalFormulaRegistry } = registries;
const { pivotTimeAdapter, toString, areDomainArgsFieldsValid } = helpers;

/**
 * @typedef {import("@odoo/o-spreadsheet").FPayload} FPayload
 * @typedef {import("@odoo/o-spreadsheet").PivotMeasure} PivotMeasure
 * @typedef {import("@odoo/o-spreadsheet").PivotDomain} PivotDomain
 * @typedef {import("@odoo/o-spreadsheet").PivotDimension} PivotDimension
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
                context: omit(
                    definition.context,
                    "pivot_measures",
                    "pivot_row_groupby",
                    "pivot_column_groupby"
                ),
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
     * @param {import("@odoo/o-spreadsheet").Maybe<FPayload>[]} args
     *
     * @returns {PivotDomain}
     */
    parseArgsToPivotDomain(args) {
        /** @type {PivotDomain} */
        const domain = [];
        const stringArgs = args.map(toString);
        for (let i = 0; i < stringArgs.length; i += 2) {
            if (stringArgs[i] === "measure") {
                domain.push({ field: stringArgs[i], value: stringArgs[i + 1] });
                continue;
            }
            const { dimensionWithGranularity, isPositional, field } = this.parseGroupField(
                stringArgs[i]
            );
            if (isPositional) {
                const previousDomain = [
                    ...domain,
                    // Need to keep the "#"
                    { field: stringArgs[i], value: stringArgs[i + 1], type: "number" },
                ];
                domain.push({
                    field: dimensionWithGranularity,
                    value: this.getLastPivotGroupValue(previousDomain),
                    type: field.type,
                });
            } else {
                domain.push({
                    field: dimensionWithGranularity,
                    value: stringArgs[i + 1],
                    type: field.type,
                });
            }
        }
        return domain;
    }

    /**
     * @param {import("@odoo/o-spreadsheet").Maybe<FPayload>[]} args
     * @returns {boolean}
     */
    areDomainArgsFieldsValid(args) {
        let dimensions = args
            .filter((_, index) => index % 2 === 0)
            .map(toString)
            .map((arg) =>
                arg === "measure" ? "measure" : this.parseGroupField(arg).dimensionWithGranularity
            );
        if (dimensions.length && dimensions.at(-1) === "measure") {
            dimensions = dimensions.slice(0, -1);
        }
        return areDomainArgsFieldsValid(dimensions, this.definition);
    }

    /**
     * Retrieves the display name of the measure with the given name from the pivot model.
     *
     * @param {string} name - The name of the measure.
     * @return {Object} - An object containing the display name of the measure.
     */
    getPivotMeasureValue(name) {
        this.assertIsValid();
        return {
            value: this.getMeasure(name).displayName,
        };
    }

    /**
     * High level method computing the result of PIVOT.HEADER functions.
     * - regular function 'PIVOT.HEADER(1,"stage_id",2,"user_id",6)'
     * - measure header 'PIVOT.HEADER(1,"stage_id",2,"user_id",6,"measure","expected_revenue")
     * - positional header 'PIVOT.HEADER(1,"#stage_id",1,"#user_id",1)'
     *
     * @param {PivotDomain} domain arguments of the function (except the first one which is the pivot id)
     * @returns {FPayload}
     */
    getPivotHeaderValueAndFormat(domain) {
        this.assertIsValid();
        const lastNode = domain.at(-1);
        if (!lastNode) {
            return { value: _t("Total") };
        }
        if (lastNode.field === "measure") {
            const measureName = lastNode.value;
            return { value: this.getMeasure(measureName).displayName };
        }
        const value = this._model.getGroupByCellValue(lastNode.field, lastNode.value);
        const format = this._getPivotFieldFormat(lastNode.field, lastNode.value);
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
     * @param {PivotDomain} domain
     * @returns {string | number | boolean}
     */
    getLastPivotGroupValue(domain) {
        this.assertIsValid();
        return this._model.getLastPivotGroupValue(domain);
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
    _getPivotFieldFormat(fieldName, value) {
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
                return timeAdapter.toValueAndFormat(value, this.getters.getLocale()).format;
            }
            default:
                return undefined;
        }
    }

    /**
     * @param {string} measureName
     * @param {PivotDomain} domain
     * @returns {FPayload}
     */
    getPivotCellValueAndFormat(measureName, domain) {
        this.assertIsValid();
        if (domain.filter((node) => node.value === NO_RECORD_AT_THIS_POSITION).length) {
            return { value: "" };
        }
        const value = this._model.getPivotCellValue(measureName, domain);
        const measure = this.getMeasure(measureName);
        let format;
        switch (measure.aggregator) {
            case "count":
            case "count_distinct":
                format = "0";
                break;
            default:
                format =
                    measure.name === "__count"
                        ? "0"
                        : this._getPivotFieldFormat(measure.name, value);
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
     * @param {PivotDomain} domain
     */
    getPivotCellDomain(domain) {
        this.assertIsValid();
        return this._model.getPivotCellDomain(domain);
    }

    /**
     * @param {PivotDimension} dimension
     * @returns {{ value: string | number | boolean, label: string }[]}
     */
    getPossibleFieldValues(dimension) {
        this.assertIsValid();
        return this._model.getPossibleFieldValues(dimension);
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
        for (const dimension of this.columns.concat(this.rows)) {
            if (
                (dimension.type === "date" || dimension.type === "datetime") &&
                !dimension.granularity
            ) {
                dimension.granularity = "month";
                dimension.nameWithGranularity = `${dimension.name}:month`;
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
    granularities: [
        "year",
        "quarter_number",
        "quarter",
        "month_number",
        "month",
        "iso_week_number",
        "week",
        "day_of_month",
        "day",
    ],
    isMeasureCandidate: (field) =>
        ((MEASURES_TYPES.includes(field.type) && field.aggregator) || field.type === "many2one") &&
        field.name !== "id" &&
        field.store,
    isGroupable: (field) => field.groupable,
});

supportedPivotPositionalFormulaRegistry.add("ODOO", true);
