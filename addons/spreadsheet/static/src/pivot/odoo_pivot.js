//@ts-check

import { Domain } from "@web/core/domain";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { NO_RECORD_AT_THIS_POSITION, OdooPivotModel } from "./pivot_model";
import { EvaluationError, PivotRuntimeDefinition, registries, helpers } from "@odoo/o-spreadsheet";
import { LOADING_ERROR } from "@spreadsheet/data_sources/data_source";
import { omit } from "@web/core/utils/objects";
import { OdooPivotLoader } from "./odoo_pivot_loader";

const { pivotRegistry, supportedPivotPositionalFormulaRegistry } = registries;
const { pivotTimeAdapter, toString, areDomainArgsFieldsValid, toNormalizedPivotValue, deepEquals } =
    helpers;

/**
 * @typedef {import("@odoo/o-spreadsheet").FunctionResultObject} FunctionResultObject
 * @typedef {import("@odoo/o-spreadsheet").PivotMeasure} PivotMeasure
 * @typedef {import("@odoo/o-spreadsheet").PivotDomain} PivotDomain
 * @typedef {import("@odoo/o-spreadsheet").PivotDimension} PivotDimension
 * @typedef {import("@odoo/o-spreadsheet").PivotCoreMeasure} PivotCoreMeasure
 * @typedef {import("@spreadsheet").WebPivotModelParams} WebPivotModelParams
 * @typedef {import("@spreadsheet").OdooPivot<OdooPivotRuntimeDefinition>} IPivot
 * @typedef {import("@spreadsheet").OdooFields} OdooFields
 * @typedef {import("@spreadsheet").OdooPivotCoreDefinition} OdooPivotCoreDefinition
 * @typedef {import("@spreadsheet").SortedColumn} SortedColumn
 * @typedef {import("@spreadsheet").OdooGetters} OdooGetters
 * @typedef {import("@spreadsheet/data_sources/odoo_data_provider").OdooDataProvider} OdooDataProvider
 */

/**
 * @implements {IPivot}
 */
export class OdooPivot {
    /**
     *
     * @override
     * @param {Object} services Services (see DataSource)
     * @param {Object} params
     * @param {OdooPivotCoreDefinition} params.definition
     * @param {OdooGetters} params.getters
     */
    constructor(services, { definition, getters }) {
        /** @type {"ODOO"} */
        this.type = "ODOO";

        /** @type {OdooPivotCoreDefinition} @protected */
        this.coreDefinition = definition;

        this.needsReevaluation = false;

        /** @type {OdooPivotRuntimeDefinition | undefined} @protected */
        this.runtimeDefinition = undefined;

        /** @type {OdooPivotModel | undefined} @protected */
        this.model = undefined;

        /** @type {OdooGetters} @protected */
        this.getters = getters;

        /** @protected */
        this.loader = new OdooPivotLoader(services.odooDataProvider, this._load.bind(this));

        /** @type {OdooFields | undefined} @protected */
        this._fields = undefined;

        /** @protected @type {OdooDataProvider}*/
        this.odooDataProvider = services.odooDataProvider;

        /** @protected @type {Object} */
        this.context = omit(
            definition.context,
            ...Object.keys(user.context),
            "pivot_measures",
            "pivot_row_groupby",
            "pivot_column_groupby"
        );

        /** @protected */
        this.domainWithGlobalFilters = this.coreDefinition.domain;
    }

    /**
     * @param {OdooPivotCoreDefinition} nextDefinition
     */
    onDefinitionChange(nextDefinition) {
        this.context = omit(nextDefinition.context, ...Object.keys(user.context));
        this.domainWithGlobalFilters = nextDefinition.domain;
        const actualDefinition = this.coreDefinition;
        this.coreDefinition = nextDefinition;
        if (
            deepEquals(actualDefinition.columns, nextDefinition.columns) &&
            deepEquals(actualDefinition.rows, nextDefinition.rows) &&
            deepEquals(actualDefinition.sortedColumn, nextDefinition.sortedColumn) &&
            deepEquals(actualDefinition.domain, nextDefinition.domain) &&
            deepEquals(actualDefinition.context, nextDefinition.context) &&
            deepEquals(actualDefinition.actionXmlId, nextDefinition.actionXmlId) &&
            deepEquals(actualDefinition.model, nextDefinition.model)
        ) {
            if (deepEquals(actualDefinition.measures, nextDefinition.measures)) {
                // Nothing change for the table structure, no need to reload the data
                return;
            }
            if (
                !this.isMeasuresChangesRequireRPC(
                    actualDefinition.measures,
                    nextDefinition.measures
                )
            ) {
                this.coreDefinition = nextDefinition;
                const runtimeDefinition = new OdooPivotRuntimeDefinition(
                    this.coreDefinition,
                    this.getFields()
                );
                this.model.updateMeasures(runtimeDefinition.measures);
                return;
            }
        }
        this.load({ reload: true });
    }

    /**
     * Check if the measures changes require a reload of the data
     *
     * A measure change requires a reload of the data if:
     * - a new non-computed measure is added
     * - a non-computed measure is removed
     * - a non-computed measure has its fieldName or aggregator changed
     *
     * @param {PivotCoreMeasure[]} actualMeasures
     * @param {PivotCoreMeasure[]} nextMeasures
     * @returns {boolean}
     */
    isMeasuresChangesRequireRPC(actualMeasures, nextMeasures) {
        const nonComputedActualMeasures = actualMeasures.filter((m) => !m.computedBy);
        const nonComputedNextMeasures = nextMeasures.filter((m) => !m.computedBy);
        if (nonComputedActualMeasures.length !== nonComputedNextMeasures.length) {
            return true;
        }
        for (const measure of nonComputedActualMeasures) {
            const updatedMeasure = nonComputedNextMeasures.find((m) => m.id === measure.id);
            if (
                !updatedMeasure ||
                updatedMeasure.fieldName !== measure.fieldName ||
                updatedMeasure.aggregator !== measure.aggregator
            ) {
                return true;
            }
        }
        return false;
    }

    async loadMetadata() {
        this._fields = await this.loader.getFields(this.coreDefinition.model);
    }

    async getModelLabel() {
        return this.loader.getModelLabel(this.coreDefinition.model);
    }

    getFields() {
        return this._fields || {};
    }

    /**
     * @param {object} [options] options for fetching data
     * @param {boolean} [options.reload=false] Force the reload of the data
     */
    init(options) {
        this.load(options);
    }

    /**
     * @param {object} [options] options for fetching data
     * @param {boolean} [options.reload=false] Force the reload of the data
     * @returns {Promise<void>}
     */
    async load(options) {
        return this.loader.load(options);
    }

    async createModelAndDefinition() {
        await this.loadMetadata();
        const definition = new OdooPivotRuntimeDefinition(this.coreDefinition, this.getFields());
        const model = new OdooPivotModel(
            { _t },
            {
                fields: this.getFields(),
                definition,
                searchParams: {
                    context: this.context,
                    domain: this.coreDefinition.domain,
                },
            },
            {
                orm: this.odooDataProvider.orm,
                serverData: this.odooDataProvider.serverData,
            }
        );
        return { model, definition };
    }

    async _load() {
        const { model, definition } = await this.createModelAndDefinition();
        this.model = model;
        this.runtimeDefinition = definition;
        await this.model.load({ context: this.context, domain: this.getDomainWithGlobalFilters() });
    }

    get definition() {
        if (!this.runtimeDefinition) {
            throw LOADING_ERROR;
        }
        return this.runtimeDefinition;
    }

    /**
     * @param {import("@odoo/o-spreadsheet").Maybe<FunctionResultObject>[]} args
     *
     * @returns {PivotDomain}
     */
    parseArgsToPivotDomain(args) {
        /** @type {PivotDomain} */
        const domain = [];
        const stringArgs = args.map(toString);
        for (let i = 0; i < stringArgs.length; i += 2) {
            const nameWithGranularity = stringArgs[i];
            if (nameWithGranularity === "measure") {
                domain.push({ field: nameWithGranularity, value: stringArgs[i + 1], type: "char" });
                continue;
            }
            const { dimensionWithGranularity, isPositional, field } =
                this.parseGroupField(nameWithGranularity);
            if (isPositional) {
                const previousDomain = [
                    ...domain,
                    // Need to keep the "#"
                    { field: nameWithGranularity, value: stringArgs[i + 1], type: "number" },
                ];
                domain.push({
                    field: dimensionWithGranularity,
                    value: this.getLastPivotGroupValue(previousDomain),
                    type: field.type,
                });
            } else {
                const normalizedValue = toNormalizedPivotValue(
                    this.definition.getDimension(dimensionWithGranularity),
                    args[i + 1]
                );
                domain.push({
                    field: dimensionWithGranularity,
                    value: normalizedValue,
                    type: field.type,
                });
            }
        }
        return domain;
    }

    /**
     * @param {import("@odoo/o-spreadsheet").Maybe<FunctionResultObject>[]} args
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
     * @returns {FunctionResultObject}
     */
    getPivotHeaderValueAndFormat(domain) {
        this.assertIsValid();
        const lastNode = domain.at(-1);
        if (!lastNode) {
            return { value: _t("Total") };
        }
        if (lastNode.field === "measure") {
            const measureId = lastNode.value;
            return { value: this.getMeasure(measureId).displayName };
        }
        const value = this.model.getGroupByCellValue(lastNode.field, lastNode.value);
        const format = this._getPivotFieldFormat(lastNode.field, lastNode.value);
        return { value, format };
    }

    /**
     * Get the measure object from its id
     *
     * @param {string} id
     * @returns {PivotMeasure}
     */
    getMeasure(id) {
        const measures = this.definition.measures;
        const measure = measures.find((m) => m.id === id);
        if (!measure) {
            throw new EvaluationError(_t("Field %s does not exist", id));
        }
        return measure;
    }

    /**
     * @param {PivotDomain} domain
     * @returns {string | number | boolean}
     */
    getLastPivotGroupValue(domain) {
        this.assertIsValid();
        return this.model.getLastPivotGroupValue(domain);
    }

    getTableStructure() {
        this.assertIsValid();
        return this.model.getTableStructure();
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
     * @param {string} measureId
     * @param {PivotDomain} domain
     * @returns {FunctionResultObject}
     */
    getPivotCellValueAndFormat(measureId, domain) {
        this.assertIsValid();
        if (domain.filter((node) => node.value === NO_RECORD_AT_THIS_POSITION).length) {
            return { value: "" };
        }
        const measure = this.getMeasure(measureId);
        const value = this.model.getPivotCellValue(measure, domain);
        let format;
        switch (measure.aggregator) {
            case "count":
            case "count_distinct":
                format = "0";
                break;
            default:
                format =
                    measure.fieldName === "__count"
                        ? "0"
                        : this._getPivotFieldFormat(measure.fieldName, value);
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
        return this.model.parseGroupField(groupFieldString);
    }

    /**
     * @param {PivotDomain} domain
     */
    getPivotCellDomain(domain) {
        this.assertIsValid();
        return this.model.getPivotCellDomain(domain);
    }

    /**
     * @param {PivotDimension} dimension
     * @returns {{ value: string | number | boolean, label: string }[]}
     */
    getPossibleFieldValues(dimension) {
        this.assertIsValid();
        return this.model.getPossibleFieldValues(dimension);
    }

    async copyModelWithOriginalDomain() {
        const { model } = await this.createModelAndDefinition();

        const domain = new Domain(this.coreDefinition.domain).toList({
            ...this.context,
            ...user.context,
        });

        const searchParams = { context: this.context, domain };
        await model.load(searchParams);
        return model;
    }

    //--------------------------------------------------------------------------
    // Loader
    //--------------------------------------------------------------------------

    get lastUpdate() {
        return this.loader.lastUpdate;
    }

    isModelValid() {
        return this.loader.isModelValid();
    }

    isValid() {
        return this.loader.isValid();
    }

    assertIsValid({ throwOnError } = { throwOnError: true }) {
        return this.loader.assertIsValid({ throwOnError });
    }

    //--------------------------------------------------------------------------
    // Global filters
    //--------------------------------------------------------------------------

    /**
     *
     * @param {string} globalFilterDomain
     */
    addGlobalFilterDomain(globalFilterDomain) {
        const domain = Domain.and([this.coreDefinition.domain, globalFilterDomain]).toString();
        if (domain.toString() === new Domain(this.domainWithGlobalFilters).toString()) {
            return;
        }
        this.domainWithGlobalFilters = domain;
        if (!this.loader.hasEverBeenLoaded()) {
            // if the data source has never been loaded, there's no point
            // at reloading it now.
            return;
        }
        this.load({ reload: true });
    }

    /**
     * Get the computed domain of this source
     * @returns {Array}
     */
    getDomainWithGlobalFilters() {
        return new Domain(this.domainWithGlobalFilters).toList({
            ...this.context,
            ...user.context,
        });
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
                dimension.nameWithGranularity = `${dimension.fieldName}:month`;
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
                activeMeasures: this.measures.filter((m) => !m.computedBy).map((m) => m.fieldName),
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

const granularities = [
    "year",
    "quarter_number",
    "quarter",
    "month_number",
    "month",
    "iso_week_number",
    "week",
    "day_of_month",
    "day",
    "day_of_week",
];

pivotRegistry.add("ODOO", {
    ui: OdooPivot,
    definition: OdooPivotRuntimeDefinition,
    externalData: true,
    onIterationEndEvaluation: () => {},
    dateGranularities: [...granularities],
    datetimeGranularities: [...granularities, "hour_number", "minute_number", "second_number"],
    isMeasureCandidate: (field) =>
        ((MEASURES_TYPES.includes(field.type) && field.aggregator) || field.type === "many2one") &&
        field.name !== "id" &&
        field.store,
    isGroupable: (field) => field.groupable,
});

supportedPivotPositionalFormulaRegistry.add("ODOO", true);
