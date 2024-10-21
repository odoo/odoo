//@ts-check

import { _t } from "@web/core/l10n/translation";
import { Domain } from "@web/core/domain";
import { sprintf } from "@web/core/utils/strings";
import { PivotModel } from "@web/views/pivot/pivot_model";

import { helpers, constants, EvaluationError, SpreadsheetPivotTable } from "@odoo/o-spreadsheet";
import { parseGroupField } from "./pivot_helpers";

const { toNormalizedPivotValue, toNumber, isDateOrDatetimeField, pivotTimeAdapter } = helpers;
const { DEFAULT_LOCALE } = constants;

/**
 * @typedef {import("@odoo/o-spreadsheet").PivotTableColumn} PivotTableColumn
 * @typedef {import("@odoo/o-spreadsheet").PivotTableRow} PivotTableRow
 * @typedef {import("@odoo/o-spreadsheet").PivotDomain} PivotDomain
 * @typedef {import("@odoo/o-spreadsheet").PivotMeasure} PivotMeasure
 */

export const NO_RECORD_AT_THIS_POSITION = "__NO_RECORD_AT_THIS_POSITION__";

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
            if (
                !updatedMeasure ||
                updatedMeasure.fieldName !== measure.fieldName ||
                updatedMeasure.aggregator !== measure.aggregator
            ) {
                throw new Error("Measures fieldName or aggregator cannot be updated");
            }
        }
        this.definition.measures = measures;
        this.resetTableStructure();
    }

    getDefinition() {
        return this.definition;
    }

    async load(searchParams) {
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
        const measurementId = this._computeMeasurementId(measure);

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
            return adapter.toValueAndFormat(value).value;
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
        this._tableStructure = undefined;
    }

    getTableStructure() {
        if (this._tableStructure === undefined) {
            // lazy build the structure
            this._tableStructure = this._buildTableStructure();
        }
        return this._tableStructure;
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
     * @returns {SpreadsheetPivotTable}
     */
    _buildTableStructure() {
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
        return new SpreadsheetPivotTable(cols, rows, measures, fieldsType);
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

    /**
     * @override
     */
    _getGroupValues(group, groupBys) {
        return groupBys.map((gb) => {
            const groupBy = this._normalize(gb);
            const { field, granularity } = this.parseGroupField(gb);
            if (isDateOrDatetimeField(field)) {
                return pivotTimeAdapter(granularity).normalizeServerValue(groupBy, field, group);
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
        let tree;
        if (this._isCol(dimensionWithGranularity)) {
            tree = this.data.colGroupTree;
            for (const col of cols) {
                tree = tree && tree.directSubTrees.get(col);
            }
        } else {
            tree = this.data.rowGroupTree;
            for (const row of rows) {
                tree = tree && tree.directSubTrees.get(row);
            }
        }
        if (tree) {
            const treeKeys = tree.sortedKeys || [...tree.directSubTrees.keys()];
            const sortedKey = treeKeys[position];
            return sortedKey !== undefined ? sortedKey : NO_RECORD_AT_THIS_POSITION;
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
                    sprintf(_t("Dimension %s is not a group by"), dimensionWithGranularity)
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
            values: group.values.map((val) => val.toString()),
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
                    values: group.values.map((val) => val.toString()),
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
     * @override
     * @protected
     * @return {string[]}
     */
    _getMeasureSpecs() {
        return this.getDefinition()
            .measures.filter((measure) => !measure.computedBy)
            .map((measure) => {
                const measurementId = `${measure.fieldName}_${measure.aggregator}_id`;
                if (measure.type === "many2one" && !measure.aggregator) {
                    return `${measure.fieldName}:count_distinct`;
                }
                if (measure.fieldName === "__count") {
                    // Remove aggregator that is not supported by python
                    return "__count";
                }
                return measure.aggregator
                    ? `${measurementId}:${measure.aggregator}(${measure.fieldName})`
                    : measure.fieldName;
            });
    }

    /**
     * @override to add the order by clause to the read_group kwargs
     */
    _getSubGroups(groupBys, params) {
        const { columns, rows } = this.getDefinition();
        const order = columns
            .concat(rows)
            .filter(
                (dimension) => dimension.order && groupBys.includes(dimension.nameWithGranularity)
            )
            .map((dimension) => `${dimension.nameWithGranularity} ${dimension.order}`)
            .join(",");
        params.kwargs.orderby = order;
        return super._getSubGroups(groupBys, params);
    }

    /**
     * This method is used to compute the identifier of a measurement in the
     * data of the web model. It's needed since we support to define an
     * aggregator for a field.
     */
    _computeMeasurementId(measure) {
        if (measure.fieldName === "__count") {
            return "__count";
        }
        if (measure.aggregator) {
            return `${measure.fieldName}_${measure.aggregator}_id`;
        }
        return measure.fieldName;
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
                const measurementId = this._computeMeasurementId(measure);
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
        const measurementId = this._computeMeasurementId(measure);
        var key = JSON.stringify(groupId);
        if (!config.data.measurements[key]) {
            return;
        }
        var values = originIndexes.map((originIndex) => {
            return config.data.measurements[key][originIndex][measurementId];
        });
        return values[0];
    }
}
