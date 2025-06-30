//@ts-check

import { _t } from "@web/core/l10n/translation";
import { Domain } from "@web/core/domain";
import { PivotModel } from "@web/views/pivot/pivot_model";

import { helpers, constants, EvaluationError, SpreadsheetPivotTable } from "@odoo/o-spreadsheet";
import { parseGroupField } from "./pivot_helpers";

const { toNormalizedPivotValue, toNumber, isDateOrDatetimeField, pivotTimeAdapter, deepEquals } =
    helpers;
const { DEFAULT_LOCALE } = constants;

/**
 * @typedef {import("@odoo/o-spreadsheet").PivotTableColumn} PivotTableColumn
 * @typedef {import("@odoo/o-spreadsheet").PivotTableRow} PivotTableRow
 * @typedef {import("@odoo/o-spreadsheet").PivotDomain} PivotDomain
 * @typedef {import("@odoo/o-spreadsheet").PivotMeasure} PivotMeasure
 */

export const NO_RECORD_AT_THIS_POSITION = "__NO_RECORD_AT_THIS_POSITION__";

/**
 * # On custom groups:
 *
 * In spreadsheet, we have a feature allowing for the user to define custom groups in pivots, ie. they can select two
 * values of a groupBy and decide to group them together. This will create a new custom field that will contains the
 * custom groups.
 *
 * The server is unaware of these custom fields, so we have to do the aggregation client side. This section will detail
 * how it is achieved. Let's take this pivot as an example:
 *
 *  _______________________________________________________________________________________________________
 * |                                |                                                                       |
 * |                                |                     Pipeline Analysis by Stage                        |
 * |                                |_______________________________________________________________________|
 * |                                |                Start               |               End                |
 * |                                |____________________________________|__________________________________|________________
 * |                                |   New            |  Qualified      |  Proposition    |  Won           |  Total         |
 * |________________________________|__________________|_________________|_________________|________________|________________|
 * |                                |    Exp. Rev.     |    Exp. Rev.    |    Exp. Rev.    |   Exp. Rev.    |   Exp. Rev.    |
 * |________________________________|__________________|_________________|_________________|________________|________________|
 * | Total                          |  $104,000.00     |  $87,300.00     |  $105,100.00    |  $23,800.00    |  $320,200.00   |
 * |________________________________|__________________|_________________|_________________|________________|________________|
 *
 * Here we have two levels of groupBy:
 * - the first one is stage_id (New, Qualified, Proposition, Won)
 * - the second one is a custom field that groups the stages into two groups: Start (New, Qualified) and
 *      End (Proposition, Won). We'll call this custom field custom_stage.
 *
 *
 * ############### RPC
 *
 * The groupBys of the pivot are then ["stage_id", "custom_stage"]. But since the server is unaware of custom_stage, we'll
 * first need to change the RPC to something the server can give us results for.
 *
 * This is done in `_getGroupsSubdivision`. The rest of the pivot model is also unaware of the custom groups, so it will
 * give the RPC parameters as if the custom group was a standard group.
 *
 * In our pivot, the `groupingSets` of the RPC will be:
 *          `[[], ["custom_stage"], ["custom_stage", "stage_id"]]`
 *
 * Simply replacing the custom_stage with it's parent groupBy, will give us:
 *          `[[], ["stage_id"], ["stage_id", "stage_id"]]`
 *
 * The server doesn't support duplicate groupBys (and they are useless), so we need a bit of processing to remove the
 * duplicates and get the grouping sets that will be used in the RPC:
 *          `[[], ["stage_id"]]`
 *
 * The server result will look something like this:
 * [
 *   {
 *     rowGroupBy: [],
 *     colGroupBy: [],
 *     subGroups: [{ "expected_revenue:sum": 320200 }],
 *   },
 *   {
 *     rowGroupBy: [],
 *     colGroupBy: ["stage_id"],
 *     subGroups: [
 *       { stage_id: [1, "New"],         "expected_revenue:sum": 104000 },
 *       { stage_id: [2, "Qualified"],   "expected_revenue:sum": 87300 },
 *       { stage_id: [3, "Proposition"], "expected_revenue:sum": 105100 },
 *       { stage_id: [4, "Won"],         "expected_revenue:sum": 23800 },
 *     ],
 *   },
 * ]
 *
 * Note that this is not included for brevity sake, but the subGroups also contain the domains and _count for each group.
 *
 *
 * ############### Aggregating subGroups
 *
 * Now that we have the subgroups, we need to aggregate them to have the value of the custom groups. This'll be done in
 * `_addCustomGroupsToGroup`, for each groupBys of our original grouping sets. Let's focus on our original grouping
 *  set of `["custom_stage"]`.
 *
 * The first step is to add the value of the custom field to all the subgroups. We'll have something like this:
 *    subGroups: [
 *       { stage_id: [1, "New"],         custom_stage: "start", "expected_revenue:sum": 104000 },
 *       { stage_id: [2, "Qualified"],   custom_stage: "start", "expected_revenue:sum": 87300 },
 *       { stage_id: [3, "Proposition"], custom_stage: "end",   "expected_revenue:sum": 105100 },
 *       { stage_id: [4, "Won"],         custom_stage: "end",   "expected_revenue:sum": 23800 },
 *     ]
 *
 *  We can now use `Object.groupBy` to group the subGroups with the same groupBy values. We'll end up with something like this:
 *  Object.groupBy result: {
 *    '["Start"]': [
 *        { stage_id: [1, "New"], "expected_revenue:sum": 104000, Stage2: "Start" },
 *        { stage_id: [2, "Qualified"], "expected_revenue:sum": 87300, Stage2: "Start" },
 *    ],
 *    '["End"]': [
 *        { stage_id: [3, "Proposition"], "expected_revenue:sum": 105100, Stage2: "End" },
 *        { stage_id: [4, "Won"], "expected_revenue:sum": 23800, Stage2: "End" },
 *    ],
 * }
 *
 * It is now simple to aggregate this (`_aggregateSubGroups`) to get our final subgroups. In our example, we just need to sum the
 * "expected_revenue:sum" for each group. The domains of each subGroups will also be aggregated with `OR` operators.
 * final subgroups: [
 *    { stage_id: [1, "New"], "expected_revenue:sum": 191300, Stage2: "Start" },
 *    { stage_id: [3, "Proposition"], "expected_revenue:sum": 128900, Stage2: "End" },
 * ]
 *
 * Note: Client side aggregation works with every aggregator but `count_distinct` where it's impossible to aggregate client-side.
 * This is why custom groups are disabled when a measure with `count_distinct` is used.
 *
 * The last step is to sort the subGroups if needed (`_sortCustomFieldsInSubGroups`), and voilà ! We have done the client-side
 * grouping of the custom fields.
 */

/**
 * This class is an extension of PivotModel with some additional information
 * that we need in spreadsheet (display_name, isUsedInSheet, ...)
 */
export class OdooPivotModel extends PivotModel {
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {import("@spreadsheet").OdooPivotModelParams} params
     * @param {import("@spreadsheet").PivotModelServices} services
     */
    constructor(env, params, services) {
        super(env, params, services);
        /**
         * @private
         */
        this._displayNames = {};
        /**
         * @private
         */
        this._displayLabels = {};
        /**
         * @private
         * @type {import("@spreadsheet/data_sources/server_data").ServerData}
         */
        this.serverData = services.serverData;

        /**
         * @type {import("@spreadsheet").OdooGetters}
         */
        this.getters = services.getters;
    }

    /**
     * @param {import("@spreadsheet").OdooPivotModelParams} params
     * @param {import("@spreadsheet").PivotModelServices} services
     */
    setup(params, services) {
        /** This is necessary to ensure the compatibility with the PivotModel from web */
        const p = params.definition.getDefinitionForPivotModel(params.fields);
        p.searchParams = {
            ...p.searchParams,
            ...params.searchParams,
        };
        super.setup(p);
        this.definition = params.definition;
    }

    /**
     * Update the parts of the pivot measures that do not impact data fetching
     * (do not update fieldName or aggregate).
     * @param {PivotMeasure[]} measures
     */
    updateMeasures(measures) {
        for (const measure of this.definition.measures) {
            const updatedMeasure = measures.find((m) => m.id === measure.id);
            if (!updatedMeasure || updatedMeasure.computedBy) {
                continue;
            }
            if (
                updatedMeasure.fieldName !== measure.fieldName ||
                updatedMeasure.aggregator !== measure.aggregator
            ) {
                throw new Error("Measures fieldName or aggregator cannot be updated");
            }
        }
        this.definition.measures = measures;
        this.resetTableStructure();
    }

    updateSortColumn(sortedColumn) {
        this.definition.sortedColumn = sortedColumn;
        this.resetTableStructure();
    }

    updateCollapsedDomains(collapsedDomains) {
        this.definition.collapsedDomains = collapsedDomains;
        this.resetTableStructure();
    }

    getDefinition() {
        return this.definition;
    }

    async load(searchParams) {
        if (
            this.metaData.activeMeasures.find(
                (fieldName) => fieldName !== "__count" && !this.metaData.fields[fieldName]
            )
        ) {
            throw new Error(
                _t(
                    "Some measures are not available: %s",
                    this.metaData.activeMeasures
                        .filter((fieldName) => !this.metaData.fields[fieldName])
                        .join(", ")
                )
            );
        }
        searchParams.groupBy = [];
        searchParams.orderBy = [];
        await super.load(searchParams);
    }

    //--------------------------------------------------------------------------
    // Evaluation
    //--------------------------------------------------------------------------

    /**
     * Get the value of the given domain for the given measure
     * @param {PivotMeasure} measure
     * @param {PivotDomain} domain
     */
    getPivotCellValue(measure, domain) {
        if (domain.some((node) => node.value === NO_RECORD_AT_THIS_POSITION)) {
            return "";
        }
        const { cols, rows } = this._getColsRowsValuesFromDomain(domain);
        const group = JSON.stringify([rows, cols]);
        const values = this.data.measurements[group];
        const measurementId = this._getAggregateSpec(measure);

        if (values && (values[0][measurementId] || values[0][measurementId] === 0)) {
            return values[0][measurementId];
        }
        return "";
    }

    /**
     * Get the value of a field
     *
     * @example
     * getGroupByCellValue("stage_id", 42) // "Won"
     *
     * @param {string} groupFieldString Name of the field
     * @param {string | number | boolean} groupValueString Value of the group by
     * @returns {string | number | boolean}
     */
    getGroupByCellValue(groupFieldString, groupValueString) {
        if (groupValueString === NO_RECORD_AT_THIS_POSITION) {
            return "";
        }
        const { field, granularity, dimensionWithGranularity } =
            this.parseGroupField(groupFieldString);
        const dimension = this.definition.getDimension(dimensionWithGranularity);
        const value = toNormalizedPivotValue(dimension, groupValueString);
        const undef = _t("None");
        if (isDateOrDatetimeField(field)) {
            const adapter = pivotTimeAdapter(granularity);
            return adapter.toValueAndFormat(value, this.getters.getLocale()).value;
        }
        if (field.relation) {
            if (value === false) {
                return undef;
            }
            return this._getRelationalDisplayName(field.relation, value);
        }
        const label = this._displayLabels[field.name]?.[value];
        if (!label) {
            return undef;
        }
        return label;
    }

    /**
     * Get the value of the last group by of the function arguments
     * e.g. in `PIVOT.HEADER(1, "stage_id", "42", "status", "won")`
     *      the last group value is "won".
     *
     * It can also handle positional arguments.
     * e.g. in `PIVOT.HEADER(1, "#stage_id", 1, "#user_id", 1)`
     *      the last group value is the id of the first user of the first stage.
     *
     * @param {PivotDomain} domain PIVOT.HEADER arguments
     * @returns {string | boolean | number}
     */
    getLastPivotGroupValue(domain) {
        const lastNode = domain.at(-1);
        if (!lastNode) {
            throw new Error("Domain size should be at least 1");
        }
        if (lastNode.field.startsWith("#")) {
            if (domain.filter((node) => node.value === NO_RECORD_AT_THIS_POSITION).length) {
                return NO_RECORD_AT_THIS_POSITION;
            }
            const { dimensionWithGranularity } = this.parseGroupField(lastNode.field);
            const { cols, rows } = this._getColsRowsValuesFromDomain(domain);
            return this._isCol(dimensionWithGranularity) ? cols.at(-1) : rows.at(-1);
        }
        return lastNode.value;
    }

    //--------------------------------------------------------------------------
    // Misc
    //--------------------------------------------------------------------------

    /**
     * Get the Odoo domain corresponding to the given domain
     * @param {PivotDomain} domain
     */
    getPivotCellDomain(domain) {
        if (domain.some((node) => node.value === NO_RECORD_AT_THIS_POSITION)) {
            return undefined;
        }
        const { cols, rows } = this._getColsRowsValuesFromDomain(domain);
        const key = JSON.stringify([rows, cols]);
        const domains = this.data.groupDomains[key];
        return domains ? domains[0] : Domain.FALSE.toList();
    }

    resetTableStructure() {
        this._collapsedTableStructure = undefined;
        this._expandedTableStructure = undefined;
    }

    getCollapsedTableStructure() {
        if (this._collapsedTableStructure === undefined) {
            // lazy build the structure
            this._collapsedTableStructure = this._buildTableStructure("collapsed");
        }
        return this._collapsedTableStructure;
    }

    getExpandedTableStructure() {
        if (this._expandedTableStructure === undefined) {
            // lazy build the structure
            this._expandedTableStructure = this._buildTableStructure("expanded");
        }
        return this._expandedTableStructure;
    }

    /**
     * @param {import("@odoo/o-spreadsheet").PivotDimension} dimension
     * @returns {{ value: string | number | boolean, label: string }[]}
     */
    getPossibleFieldValues(dimension) {
        const valuesWithLabels = [];
        const valuesUniqueness = new Set();
        const isCol = this._isCol(dimension.nameWithGranularity);
        const groupBys = isCol ? this.definition.columns : this.definition.rows;
        const tree = isCol ? this.data.colGroupTree : this.data.rowGroupTree;
        const groupByIndex = groupBys.findIndex(
            (d) => d.nameWithGranularity === dimension.nameWithGranularity
        );
        const visitTree = (tree) => {
            const { values, labels } = tree.root;
            const value = values[groupByIndex];
            if (value !== undefined && !valuesUniqueness.has(value)) {
                valuesUniqueness.add(value);
                valuesWithLabels.push({
                    value: value,
                    label: labels[groupByIndex].toString(),
                });
            }
            [...tree.directSubTrees.values()].forEach((subTree) => {
                visitTree(subTree);
            });
        };
        visitTree(tree);
        return valuesWithLabels;
    }

    /**
     * Build the table structure
     * @param {"collapsed" | "expanded"} mode
     * @returns {SpreadsheetPivotTable}
     */
    _buildTableStructure(mode) {
        const cols = this._getSpreadsheetCols();
        const rows = this._getSpreadsheetRows(this.data.rowGroupTree);
        rows.push(rows.shift()); //Put the Total row at the end.
        const measures = this.getDefinition()
            .measures.filter((measure) => !measure.isHidden)
            .map((measure) => measure.id);
        /** @type {Record<string, string | undefined>} */
        const fieldsType = {};
        for (const columns of this.getDefinition().columns) {
            fieldsType[columns.fieldName] = columns.type;
        }
        for (const row of this.getDefinition().rows) {
            fieldsType[row.fieldName] = row.type;
        }
        const collapsedDomains =
            mode === "collapsed" ? this.getDefinition().collapsedDomains : undefined;
        return new SpreadsheetPivotTable(cols, rows, measures, fieldsType, collapsedDomains);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _loadData(config) {
        /** @type {(groupFieldString: string) => ReturnType<parseGroupField>} */
        this.parseGroupField = parseGroupField.bind(null, this.metaData.fields);
        /*
         * prune is manually set to false in order to expand all the groups
         * automatically
         */
        const prune = false;
        await super._loadData(config, prune);

        const registerLabels = (tree, groupBys) => {
            const group = tree.root;
            if (!tree.directSubTrees.size) {
                for (let i = 0; i < group.values.length; i++) {
                    const { field } = this.parseGroupField(groupBys[i]);
                    if (!field.relation) {
                        this._registerDisplayLabel(field.name, group.values[i], group.labels[i]);
                    } else {
                        const id = group.values[i];
                        const displayName = group.labels[i];
                        this._registerDisplayName(field.relation, id, displayName);
                    }
                }
            }
            [...tree.directSubTrees.values()].forEach((subTree) => {
                registerLabels(subTree, groupBys);
            });
        };

        registerLabels(this.data.colGroupTree, this.metaData.fullColGroupBys);
        registerLabels(this.data.rowGroupTree, this.metaData.fullRowGroupBys);
    }

    _registerDisplayLabel(fieldName, value, label) {
        if (!this._displayLabels[fieldName]) {
            this._displayLabels[fieldName] = {};
        }
        this._displayLabels[fieldName][value] = label;
    }

    _registerDisplayName(resModel, resId, displayName) {
        if (!this._displayNames[resModel]) {
            this._displayNames[resModel] = {};
        }
        this._displayNames[resModel][resId] = displayName;
    }

    _getRelationalDisplayName(resModel, resId) {
        const displayName =
            this._displayNames[resModel]?.[resId] ||
            this.serverData.batch.get("spreadsheet.mixin", "get_display_names_for_spreadsheet", {
                model: resModel,
                id: resId,
            });
        if (!displayName) {
            throw new EvaluationError(
                _t("Unable to fetch the label of %(id)s of model %(model)s", {
                    id: resId,
                    model: resModel,
                })
            );
        }
        return displayName;
    }

    _normalize(groupBy) {
        const [fieldName] = groupBy.split(":");
        const field = this.metaData.fields[fieldName];
        if (!field) {
            throw new EvaluationError(_t("Field %s does not exist", fieldName));
        }
        return super._normalize(groupBy);
    }

    /**
     * @override
     */
    _getGroupValues(group, groupBys) {
        return groupBys.map((gb) => {
            const groupBy = this._normalize(gb);
            const { field, granularity } = this.parseGroupField(gb);
            if (isDateOrDatetimeField(field)) {
                return pivotTimeAdapter(granularity).normalizeServerValue(
                    groupBy,
                    field,
                    group,
                    this.getters.getLocale()
                );
            }
            return this._sanitizeValue(group[groupBy]);
        });
    }

    /**
     * Check if the given field is used as col group by
     */
    _isCol(nameWithGranularity) {
        return this.metaData.fullColGroupBys.includes(nameWithGranularity);
    }

    /**
     * Check if the given field is used as row group by
     */
    _isRow(nameWithGranularity) {
        return this.metaData.fullRowGroupBys.includes(nameWithGranularity);
    }

    /**
     * Get the value of a field-value for a positional group by
     *
     * @param {string} dimensionWithGranularity e.g. create_date:month
     * @param {unknown} groupValueString Value of the group by
     * @param {(number | boolean | string)[]} rows Values for the previous row group bys
     * @param {(number | boolean | string)[]} cols Values for the previous col group bys
     *
     * @private
     * @returns {number | boolean | string}
     */
    _parsePivotFormulaWithPosition(dimensionWithGranularity, groupValueString, cols, rows) {
        const position = toNumber(groupValueString, DEFAULT_LOCALE) - 1;
        const table = this.getExpandedTableStructure();
        let tree;
        if (this._isCol(dimensionWithGranularity)) {
            tree = table.getColTree();
            for (const col of cols) {
                tree = tree && tree.find((child) => child.value === col)?.children;
            }
        } else {
            tree = table.getRowTree();
            for (const row of rows) {
                tree = tree && tree.find((child) => child.value === row)?.children;
            }
        }
        if (tree) {
            const value = tree[position]?.value;
            return value !== undefined ? value : NO_RECORD_AT_THIS_POSITION;
        }
        return NO_RECORD_AT_THIS_POSITION;
    }

    /**
     * Transform the given domain in the structure used in this class
     *
     * @param {PivotDomain} domain Domain
     *
     * @private
     */
    _getColsRowsValuesFromDomain(domain) {
        const rows = [];
        const cols = [];
        for (const node of domain) {
            const { isPositional, dimensionWithGranularity } = this.parseGroupField(node.field);
            let value;
            if (isPositional) {
                value = this._parsePivotFormulaWithPosition(
                    dimensionWithGranularity,
                    node.value,
                    cols,
                    rows
                );
            } else {
                const dimension = this.definition.getDimension(dimensionWithGranularity);
                value = toNormalizedPivotValue(dimension, node.value);
            }
            if (this._isCol(dimensionWithGranularity)) {
                cols.push(value);
            } else if (this._isRow(dimensionWithGranularity)) {
                rows.push(value);
            } else {
                throw new EvaluationError(
                    _t("Dimension %s is not a group by", dimensionWithGranularity)
                );
            }
        }
        return { rows, cols };
    }

    /**
     * Get the row structure
     * @returns {PivotTableRow[]}
     */
    _getSpreadsheetRows(tree) {
        /**@type {PivotTableRow[]}*/
        const rows = [];
        const group = tree.root;
        const indent = group.labels.length;
        const rowGroupBys = this.metaData.fullRowGroupBys;

        rows.push({
            fields: rowGroupBys.slice(0, indent),
            values: group.values.map((val) => val),
            indent,
        });

        const subTreeKeys = tree.sortedKeys || [...tree.directSubTrees.keys()];
        subTreeKeys.forEach((subTreeKey) => {
            const subTree = tree.directSubTrees.get(subTreeKey);
            rows.push(...this._getSpreadsheetRows(subTree));
        });
        return rows;
    }

    /**
     * Get the col structure
     * @returns {PivotTableColumn[][]}
     */
    _getSpreadsheetCols() {
        const colGroupBys = this.metaData.fullColGroupBys;
        const height = colGroupBys.length;
        const measures = this.getDefinition().measures.filter((measure) => !measure.isHidden);
        const measureCount = measures.length;
        const leafCounts = this._getLeafCounts(this.data.colGroupTree);

        const headers = new Array(height).fill(0).map(() => []);

        function generateTreeHeaders(tree, fields) {
            const group = tree.root;
            const rowIndex = group.values.length;
            if (rowIndex !== 0) {
                const row = headers[rowIndex - 1];
                const leafCount = leafCounts[JSON.stringify(tree.root.values)];
                const cell = {
                    fields: colGroupBys.slice(0, rowIndex),
                    values: group.values.map((val) => val),
                    width: leafCount * measureCount,
                };
                row.push(cell);
            }

            [...tree.directSubTrees.values()].forEach((subTree) => {
                generateTreeHeaders(subTree, fields);
            });
        }

        generateTreeHeaders(this.data.colGroupTree, this.metaData.fields);
        const hasColGroupBys = this.metaData.colGroupBys.length;

        // 2) generate measures row
        const measureRow = [];

        if (hasColGroupBys) {
            headers[headers.length - 1].forEach((cell) => {
                measures.forEach((measure) => {
                    const measureCell = {
                        fields: [...cell.fields, "measure"],
                        values: [...cell.values, measure.id],
                        width: 1,
                    };
                    measureRow.push(measureCell);
                });
            });
        }
        measures.forEach((measure) => {
            const measureCell = {
                fields: ["measure"],
                values: [measure.id],
                width: 1,
            };
            measureRow.push(measureCell);
        });
        headers.push(measureRow);
        // 3) Add the total cell
        if (headers.length === 1) {
            headers.unshift([]); // Will add the total there
        }
        headers[headers.length - 2].push({
            fields: [],
            values: [],
            width: measures.length,
        });

        return headers;
    }

    /**
     * This method is used to compute the aggregate spec of a measurement in the
     * data of the web model. It's needed since we support to define an
     * aggregator for a field.
     */
    _getAggregateSpec(measure) {
        if (measure.fieldName === "__count") {
            return "__count";
        }
        if (measure.aggregator) {
            return `${measure.fieldName}:${measure.aggregator}`;
        }
        if (measure.type === "many2one") {
            return `${measure.fieldName}:count_distinct`;
        }
        const field = this.metaData.fields[measure.fieldName];
        if (!field.aggregator) {
            throw new Error(`Field ${measure.fieldName} doesn't have a default aggregator`);
        }
        return `${measure.fieldName}:${field.aggregator}`;
    }

    /**
     * @override
     * @protected
     * @return {string[]}
     */
    _getMeasureSpecs() {
        return this.getDefinition()
            .measures.filter((measure) => !measure.computedBy)
            .map(this._getAggregateSpec, this);
    }

    /**
     * @override to add the order by clause to the read_group kwargs
     */
    async _getGroupsSubdivision(params, groupInfo) {
        const customFields = this.definition.customFields || {};

        const { columns, rows } = this.getDefinition();
        const allGroupBys = params.groupingSets.flat();
        const order = columns
            .concat(rows)
            .filter(
                (dimension) =>
                    dimension.order && allGroupBys.includes(dimension.nameWithGranularity)
            )
            .map((dimension) => `${dimension.nameWithGranularity} ${dimension.order}`)
            .join(",");
        params.kwargs.order = order;

        const hasCustomField = allGroupBys.some((gb) => customFields[gb] !== undefined);
        if (!hasCustomField) {
            return await super._getGroupsSubdivision(params, groupInfo);
        } else if (params.measureSpecs.some((measure) => measure.endsWith(":count_distinct"))) {
            throw new Error(_t('Cannot use custom pivot groups with "Count Distinct" measure'));
        } else {
            return this._doCustomGroupSubdivision(params, groupInfo);
        }
    }

    _aggregateSubGroups(subGroups, measures) {
        if (subGroups.length === 1) {
            return subGroups[0];
        }
        const subGroup = { ...subGroups[0] };
        for (const measure of measures) {
            const aggregator = measure.split(":")[1];
            switch (aggregator) {
                case "sum":
                case "count":
                    subGroup[measure] = subGroups.reduce((sum, sg) => sum + sg[measure], 0);
                    break;
                case "min":
                    subGroup[measure] = Math.min(...subGroups.map((sg) => sg[measure]));
                    break;
                case "max":
                    subGroup[measure] = Math.max(...subGroups.map((sg) => sg[measure]));
                    break;
                case "avg": {
                    const totalCount = subGroups.reduce((sum, sg) => sum + (sg.__count || 0), 0);
                    if (totalCount === 0) {
                        subGroup[measure] = 0;
                    } else {
                        subGroup[measure] =
                            subGroups.reduce((sum, sg) => sum + sg[measure] * sg.__count, 0) /
                            totalCount;
                    }
                    break;
                }
            }
        }
        subGroup.__count = subGroups.reduce((sum, sg) => sum + (sg.__count || 0), 0);

        const domains = subGroups.map((sg) => sg.__domain || []);
        subGroup.__domain = Domain.combine(domains, "OR").toList();
        const extraDomains = subGroups.map((sg) => sg.__extraDomain || []);
        subGroup.__extraDomain = Domain.combine(extraDomains, "OR").toList();

        return subGroup;
    }

    _sortCustomFieldsInSubGroups(groupBys, subGroups) {
        const isInOthersGroup = (subGroup, groupBy, customField) => {
            const value = Array.isArray(subGroup[groupBy])
                ? subGroup[groupBy][0]
                : subGroup[groupBy];
            const otherGroup = customField.groups.find((g) => g.isOtherGroup);
            return otherGroup && value === otherGroup.name;
        };

        const sortFn = (subGroupA, subGroupB, order, groupBy, customField) => {
            if (isInOthersGroup(subGroupB, groupBy, customField)) {
                return -1;
            }
            if (isInOthersGroup(subGroupA, groupBy, customField)) {
                return 1;
            }
            const aValue = subGroupA[groupBy];
            const bValue = subGroupB[groupBy];
            if (aValue === false) {
                return order === "asc" ? 1 : -1;
            } else if (bValue === false) {
                return order === "asc" ? -1 : 1;
            }

            const aLabel = (Array.isArray(aValue) ? aValue[1] : String(aValue)).toLowerCase();
            const bLabel = (Array.isArray(bValue) ? bValue[1] : String(bValue)).toLowerCase();
            return order === "asc" ? aLabel.localeCompare(bLabel) : bLabel.localeCompare(aLabel);
        };

        const sortSubGroups = (groupBys, subGroups) => {
            const groupBy = groupBys[0];
            const childrenMap = new Map();

            for (const item of subGroups) {
                const value = item[groupBy];
                const key = Array.isArray(value) ? value[0] : value;
                if (!childrenMap.has(key)) {
                    childrenMap.set(key, []);
                }
                childrenMap.get(key).push(item);
            }

            // Sort group keys
            const customField = this.definition.customFields?.[groupBy];
            const keys = Array.from(childrenMap.keys());
            const order = this.definition.getDimension(groupBy)?.order;

            if (customField && order) {
                keys.sort((a, b) => {
                    const subGroupB = childrenMap.get(b)[0];
                    const subGroupA = childrenMap.get(a)[0];
                    return sortFn(subGroupA, subGroupB, order, groupBy, customField);
                });
            }

            return keys.flatMap((key) =>
                groupBys.length > 1
                    ? sortSubGroups(groupBys.slice(1), childrenMap.get(key))
                    : childrenMap.get(key)
            );
        };

        return sortSubGroups(groupBys, subGroups);
    }

    /**
     * If the measures can be aggregated client side (not `count_distinct`), we can do a single RPC to get all the
     * subgroups, then do a Object.groupBy() client side to aggregate the subgroups.
     *
     * See comment at the start of the file for more details.
     */
    async _doCustomGroupSubdivision(params, groupInfo) {
        const customFields = this.definition.customFields || {};

        const mockGroupInfo = groupInfo.map((info) => ({
            ...info,
            rowGroupBy: info.rowGroupBy.map((gb) => customFields[gb]?.parentField || gb),
            colGroupBy: info.colGroupBy.map((gb) => customFields[gb]?.parentField || gb),
        }));

        // Grouping sets need to be unique, but with custom groups some might be duplicated. It happens when we do
        // something like groupBy=[grouped:user_id, user_id], we only want to fetch groupBy=[user_id]
        const groupInfoKeysSet = new Set();
        const uniqueGroupInfo = [];
        for (const info of mockGroupInfo) {
            const { rowGroupBy, colGroupBy } = info;
            const uniqueGroups = [...new Set([...rowGroupBy, ...colGroupBy].sort())].join(",");
            if (!groupInfoKeysSet.has(uniqueGroups)) {
                uniqueGroupInfo.push({
                    ...info,
                    rowGroupBy,
                    colGroupBy,
                    subGroupIndex: groupInfoKeysSet.size,
                });
                groupInfoKeysSet.add(uniqueGroups);
            }
        }
        const uniqueGroupingSets = [...groupInfoKeysSet].map((key) =>
            key.split(",").filter((gb) => gb !== "")
        );

        // Remove custom groups from order
        if (params.kwargs.order) {
            const fieldNameRegex = /(.*) (asc|desc)/;
            params.kwargs.order = params.kwargs.order
                .split(",")
                .filter((part) => {
                    const groupBy = part.match(fieldNameRegex)?.[1];
                    return customFields[groupBy] === undefined;
                })
                .join(",");
        }

        const result = await super._getGroupsSubdivision(
            { ...params, groupingSets: uniqueGroupingSets },
            uniqueGroupInfo
        );

        const resultWithCustomGroups = [];
        for (let i = 0; i < groupInfo.length; i++) {
            const info = groupInfo[i];
            const mockInfo = mockGroupInfo[i];
            const mockGroupBys = [
                ...new Set([...mockInfo.rowGroupBy, ...mockInfo.colGroupBy].sort()),
            ];
            const resultIndex = uniqueGroupingSets.findIndex((groups) =>
                deepEquals(groups, mockGroupBys)
            );
            const subGroups = result[resultIndex].subGroups;

            const groupBys = [...info.rowGroupBy, ...info.colGroupBy];
            const hasCustomField = groupBys.some((gb) => customFields[gb] !== undefined);
            if (hasCustomField) {
                resultWithCustomGroups.push(this._addCustomGroupsToGroup(params, info, subGroups));
            } else {
                resultWithCustomGroups.push({ ...info, subGroups });
            }
        }
        return resultWithCustomGroups;
    }

    _addCustomGroupsToGroup(params, groupInfo, subGroups) {
        const customFields = this.definition.customFields || {};
        const { rowGroupBy, colGroupBy } = groupInfo;
        const groupBys = [...rowGroupBy, ...colGroupBy];

        for (const groupBy of groupBys) {
            const customField = customFields[groupBy];
            if (!customField) {
                continue;
            }

            for (const subGroup of subGroups) {
                const parentFieldName = customField.parentField;
                const parentValue = Array.isArray(subGroup[parentFieldName])
                    ? subGroup[parentFieldName][0]
                    : subGroup[parentFieldName];
                const group =
                    customField.groups.find((g) => g.values.includes(parentValue)) ||
                    customField.groups.find((g) => g.isOtherGroup);

                subGroup[groupBy] = group ? group.name : subGroup[parentFieldName];
            }
        }

        // Note: we need to preserve the order of the subGroups from the server. Object.groupBy() has no guarantee
        // on the order of keys, but its implementation in major browsers does seem to preserve the order. We'll use
        // Object.groupBy() until we find practical issues with it.
        const getKey = (subGroup) => JSON.stringify(groupBys.map((groupBy) => subGroup[groupBy]));
        const groupedSubgroups = Object.groupBy(subGroups, getKey);

        const aggregatedSubgroups = Object.values(groupedSubgroups).map((subGroups) =>
            this._aggregateSubGroups(subGroups, params.measureSpecs)
        );
        const sortedSubGroups = this._sortCustomFieldsInSubGroups(groupBys, aggregatedSubgroups);

        return { ...groupInfo, subGroups: sortedSubGroups };
    }

    /**
     * Override to support multiple aggregators for a same field
     *
     * @override
     */
    _getMeasurements(group) {
        return this.getDefinition()
            .measures.filter((measure) => !measure.computedBy)
            .reduce((measurements, measure) => {
                const measurementId = this._getAggregateSpec(measure);
                var measurement = group[measurementId];
                if (measurement instanceof Array) {
                    // case field is many2one and used as measure and groupBy simultaneously
                    measurement = 1;
                }
                if (measure.type === "boolean" && measurement instanceof Boolean) {
                    measurement = measurement ? 1 : 0;
                }
                measurements[measurementId] = measurement;
                return measurements;
            }, {});
    }

    /**
     * Override to support multiple aggregators for a same field
     *
     * @override
     */
    _getCellValue(groupId, measureName, originIndexes, config) {
        const measure = this.getDefinition().measures.find((m) => m.fieldName === measureName);
        const measurementId = this._getAggregateSpec(measure);
        var key = JSON.stringify(groupId);
        if (!config.data.measurements[key]) {
            return;
        }
        var values = originIndexes.map(
            (originIndex) => config.data.measurements[key][originIndex][measurementId]
        );
        return values[0];
    }
}
