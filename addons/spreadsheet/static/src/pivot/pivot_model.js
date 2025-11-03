// @ts-check
import { _t } from "@web/core/l10n/translation";
import { Domain } from "@web/core/domain";
import { parseGroupField } from "./pivot_helpers";
import { helpers, constants, EvaluationError, SpreadsheetPivotTable } from "@odoo/o-spreadsheet";

const { toNormalizedPivotValue, toNumber, isDateOrDatetimeField, pivotTimeAdapter } = helpers;
const { DEFAULT_LOCALE } = constants;

export const NO_RECORD_AT_THIS_POSITION = "__NO_RECORD_AT_THIS_POSITION__";

/**
 * @typedef {import("@web/core/orm_service").ORM} ORM
 * @typedef {import("@spreadsheet/data_sources/server_data").ServerData} ServerData
 * @typedef {import("@spreadsheet").OdooGetters} OdooGetters
 * @typedef {import("@spreadsheet/pivot/odoo_pivot").OdooPivotRuntimeDefinition} OdooPivotRuntimeDefinition
 * @typedef {import("@spreadsheet/pivot/pivot_data_provider").PivotDataProvider} PivotDataProvider
 * @typedef {import("@odoo/o-spreadsheet").PivotMeasure} PivotMeasure
 * @typedef {import("@odoo/o-spreadsheet").PivotDomain} PivotDomain
 * @typedef {import("@odoo/o-spreadsheet").PivotDimension} PivotDimension
 */

export class OdooPivotModel {
    /**
     * @param {OdooPivotRuntimeDefinition} definition
     * @param {PivotDataProvider} pivotDataProvider
     * @param {OdooGetters} getters
     */
    constructor(definition, pivotDataProvider, getters) {
        this.definition = definition;
        this.getters = getters;
        this.pivotDataProvider = pivotDataProvider;

        this._displayNames = {};
        this._displayLabels = {};

        this.data = {};
        this.domain = [];
        this.context = {};
        this.colGroupBys = this.definition.columns.map((c) => c.nameWithGranularity);
        this.rowGroupBys = this.definition.rows.map((r) => r.nameWithGranularity);
        this.parseGroupField = parseGroupField.bind(null, this.definition.fields);
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    async load({ context, domain }) {
        this.domain = domain;
        this.context = context;
        this.data = {
            rowGroupTree: { root: { labels: [], values: [] }, directSubTrees: new Map() },
            colGroupTree: { root: { labels: [], values: [] }, directSubTrees: new Map() },
            measurements: {},
            counts: {},
            groupDomains: {
                [JSON.stringify([[], []])]: this.domain,
            },
            numbering: {},
        };
        const groupSubdivisions = await this.pivotDataProvider.load({ context, domain });
        if (groupSubdivisions.length) {
            const group = { rowValues: [], colValues: [] };
            this._prepareData(group, groupSubdivisions);
        }

        this._registerLabels(this.data.colGroupTree, this.colGroupBys);
        this._registerLabels(this.data.rowGroupTree, this.rowGroupBys);
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
    }

    updateCollapsedDomains(collapsedDomains) {
        this.definition.collapsedDomains = collapsedDomains;
        this.resetTableStructure();
    }

    //--------------------------------------------------------------------------
    // Protected
    //--------------------------------------------------------------------------

    _registerLabels(tree, groupBys) {
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
            this._registerLabels(subTree, groupBys);
        });
    }

    /**
     * Add labels/values in the provided groupTree. A new leaf is created in
     * the groupTree with a root object corresponding to the group with given
     * labels/values.
     *
     * @protected
     * @param {Object} groupTree, either this.data.rowGroupTree or this.data.colGroupTree
     * @param {string[]} labels
     * @param {Array} values
     */
    _addGroup(groupTree, labels, values) {
        let tree = groupTree;
        // we assume here that the group with value value.slice(value.length - 2) has already been added.
        values.slice(0, values.length - 1).forEach(function (value) {
            tree = tree.directSubTrees.get(value);
        });
        const value = values[values.length - 1];
        if (tree.directSubTrees.has(value)) {
            return;
        }
        tree.directSubTrees.set(value, {
            root: {
                labels: labels,
                values: values,
            },
            directSubTrees: new Map(),
        });
    }
    /**
     * Find a group with given values in the provided groupTree, either
     * this.rowGrouptree or this.data.colGroupTree.
     *
     * @protected
     * @param {Object} groupTree
     * @param {Array} values
     * @returns {Object}
     */
    _findGroup(groupTree, values) {
        let tree = groupTree;
        values.slice(0, values.length).forEach((value) => {
            tree = tree.directSubTrees.get(value);
        });
        return tree;
    }
    /**
     * Returns the group sanitized labels.
     *
     * @protected
     * @param {Object} group
     * @param {string[]} groupBys
     * @returns {string[]}
     */
    _getGroupLabels(group, groupBys) {
        return groupBys.map((gb) => this._sanitizeLabel(group[gb], gb));
    }

    /**
     * Returns the group sanitized values.
     *
     * @protected
     * @param {Object} group
     * @param {string[]} groupBys
     * @returns {Array}
     */
    _getGroupValues(group, groupBys) {
        return groupBys.map((groupBy) => {
            const { field, granularity } = this.parseGroupField(groupBy);
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
     * Returns the leaf counts of each group inside the given tree.
     *
     * @protected
     * @param {Object} tree
     * @returns {Object} keys are group ids
     */
    _getLeafCounts(tree) {
        const leafCounts = {};
        let leafCount;
        if (!tree.directSubTrees.size) {
            leafCount = 1;
        } else {
            leafCount = [...tree.directSubTrees.values()].reduce((acc, subTree) => {
                const subLeafCounts = this._getLeafCounts(subTree);
                Object.assign(leafCounts, subLeafCounts);
                return acc + leafCounts[JSON.stringify(subTree.root.values)];
            }, 0);
        }

        leafCounts[JSON.stringify(tree.root.values)] = leafCount;
        return leafCounts;
    }

    _getMeasurements(group) {
        return this.definition.measures
            .filter((measure) => !measure.computedBy)
            .reduce((measurements, measure) => {
                const measurementId = this._getAggregateSpec(measure);
                let measurement = group[measurementId];
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

        if (values && (values[measurementId] || values[measurementId] === 0)) {
            return values[measurementId];
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
        return this.data.groupDomains[key] || Domain.FALSE.toList();
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
     * @param {PivotDimension} dimension
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
        const measures = this.definition.measures
            .filter((measure) => !measure.isHidden)
            .map((measure) => measure.id);
        /** @type {Record<string, string | undefined>} */
        const fieldsType = {};
        for (const columns of this.definition.columns) {
            fieldsType[columns.fieldName] = columns.type;
        }
        for (const row of this.definition.rows) {
            fieldsType[row.fieldName] = row.type;
        }
        const collapsedDomains =
            mode === "collapsed" ? this.definition.collapsedDomains : undefined;
        return new SpreadsheetPivotTable(cols, rows, measures, fieldsType, collapsedDomains);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

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
        const rowGroupBys = this.rowGroupBys;

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
        const colGroupBys = this.colGroupBys;
        const height = colGroupBys.length;
        const measures = this.definition.measures.filter((measure) => !measure.isHidden);
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

        generateTreeHeaders(this.data.colGroupTree, this.definition.fields);
        const hasColGroupBys = this.colGroupBys.length;

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
        const field = this.definition.fields[measure.fieldName];
        if (!field.aggregator) {
            throw new Error(`Field ${measure.fieldName} doesn't have a default aggregator`);
        }
        return `${measure.fieldName}:${field.aggregator}`;
    }
    /**
     * Make sure that the labels of different many2one values are distinguished
     * by numbering them if necessary.
     *
     * @protected
     * @param {Array} label
     * @param {string} fieldName
     * @returns {string}
     */
    _getNumberedLabel(label, fieldName) {
        const id = label[0];
        const name = label[1];
        this.data.numbering[fieldName] = this.data.numbering[fieldName] || {};
        this.data.numbering[fieldName][name] = this.data.numbering[fieldName][name] || {};
        const numbers = this.data.numbering[fieldName][name];
        numbers[id] = numbers[id] || Object.keys(numbers).length + 1;
        return name + (numbers[id] > 1 ? "  (" + numbers[id] + ")" : "");
    }

    _registerDisplayLabel(fieldName, value, label) {
        if (!this._displayLabels[fieldName]) {
            this._displayLabels[fieldName] = {};
        }
        this._displayLabels[fieldName][value] = label;
    }

    /**
     * @param {string} resModel
     * @param {number} resId
     * @param {string} displayName
     */
    _registerDisplayName(resModel, resId, displayName) {
        if (!this._displayNames[resModel]) {
            this._displayNames[resModel] = {};
        }
        this._displayNames[resModel][resId] = displayName;
    }

    /**
     * @param {string} resModel
     * @param {number} resId
     * @returns {string}
     */
    _getRelationalDisplayName(resModel, resId) {
        let displayName = this._displayNames[resModel]?.[resId];
        if (displayName) {
            return displayName;
        }
        displayName = this.pivotDataProvider.loadRelationalDisplayName(resModel, resId);
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

    /**
     * Extract the information in the read_group results (groupSubdivisions)
     * and develop this.data.rowGroupTree, colGroupTree, measurements, counts, and
     * groupDomains.
     * If a column needs to be sorted, the rowGroupTree corresponding to the
     * group is sorted.
     *
     * @protected
     * @param {Object} group
     * @param {Object[]} groupSubdivisions
     */
    _prepareData(group, groupSubdivisions) {
        const groupRowValues = group.rowValues;
        let groupRowLabels = [];
        let rowSubTree = this.data.rowGroupTree;
        let root;
        if (groupRowValues.length) {
            // we should have labels information on hand! regretful!
            rowSubTree = this._findGroup(this.data.rowGroupTree, groupRowValues);
            root = rowSubTree.root;
            groupRowLabels = root.labels;
        }

        const groupColValues = group.colValues;
        let groupColLabels = [];
        if (groupColValues.length) {
            root = this._findGroup(this.data.colGroupTree, groupColValues).root;
            groupColLabels = root.labels;
        }

        groupSubdivisions.forEach((groupSubdivision) => {
            groupSubdivision.subGroups.forEach((subGroup) => {
                const rowValues = groupRowValues.concat(
                    this._getGroupValues(subGroup, groupSubdivision.rowGroupBy)
                );
                const rowLabels = groupRowLabels.concat(
                    this._getGroupLabels(subGroup, groupSubdivision.rowGroupBy)
                );

                const colValues = groupColValues.concat(
                    this._getGroupValues(subGroup, groupSubdivision.colGroupBy)
                );
                const colLabels = groupColLabels.concat(
                    this._getGroupLabels(subGroup, groupSubdivision.colGroupBy)
                );

                if (!colValues.length && rowValues.length) {
                    this._addGroup(this.data.rowGroupTree, rowLabels, rowValues);
                }
                if (colValues.length && !rowValues.length) {
                    this._addGroup(this.data.colGroupTree, colLabels, colValues);
                }

                const key = JSON.stringify([rowValues, colValues]);

                this.data.measurements[key] = this._getMeasurements(subGroup);
                this.data.counts[key] = subGroup.__count;

                // if __domain is not defined this means that we are in the
                // case where
                // groupSubdivision.rowGroupBy = groupSubdivision.rowGroupBy = []
                if (subGroup.__domain) {
                    this.data.groupDomains[key] = subGroup.__domain;
                } else {
                    this.data.groupDomains[key] = Domain.FALSE.toList();
                }
            });
        });
    }

    /**
     * Extract from a groupBy value a label.
     *
     * @protected
     * @param {any} value
     * @param {string} groupBy
     * @returns {string}
     */
    _sanitizeLabel(value, groupBy) {
        const fieldName = groupBy.split(":")[0];
        if (fieldName && this.definition.fields[fieldName]) {
            const fields = fieldName.split(".");
            if (fields.length > 1 && fields.at(-1) === "id" && Array.isArray(value)) {
                return value[0];
            }
        }
        if (fieldName && this.definition.fields[fieldName]) {
            const field = this.definition.fields[fieldName];
            if (field.type === "boolean") {
                return value === undefined ? _t("None") : value ? _t("Yes") : _t("No");
            } else if (field.type === "integer") {
                if (fieldName === "id" && Array.isArray(value)) {
                    return value[1];
                }
                return value || "0";
            }
        }
        if (value === false) {
            return this.definition.fields[fieldName].falsy_value_label || _t("None");
        }
        if (value instanceof Array) {
            return this._getNumberedLabel(value, fieldName);
        }
        if (this.definition.fields[fieldName]?.type === "selection") {
            const selected = this.definition.fields[fieldName].selection.find(
                (o) => o[0] === value
            );
            return selected ? selected[1] : value; // selected should be truthy normally ?!
        }
        return value;
    }
    /**
     * Extract from a groupBy value the raw value of that groupBy (discarding
     * a label if any)
     *
     * @protected
     * @param {any} value
     * @returns {any}
     */
    _sanitizeValue(value) {
        if (value instanceof Array) {
            return value[0];
        }
        return value;
    }

    /**
     * Check if the given field is used as col group by
     * @param {string} nameWithGranularity
     */
    _isCol(nameWithGranularity) {
        return this.colGroupBys.includes(nameWithGranularity);
    }

    /**
     * Check if the given field is used as row group by
     * @param {string} nameWithGranularity
     */
    _isRow(nameWithGranularity) {
        return this.rowGroupBys.includes(nameWithGranularity);
    }
}
