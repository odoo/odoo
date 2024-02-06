/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { Domain } from "@web/core/domain";
import { sprintf } from "@web/core/utils/strings";
import { PivotModel } from "@web/views/pivot/pivot_model";

import { helpers, constants, EvaluationError } from "@odoo/o-spreadsheet";
import { SpreadsheetPivotTable } from "@spreadsheet/pivot/pivot_table";
import { pivotTimeAdapter } from "./pivot_time_adapters";
import { OdooPivotDataSource } from "./pivot_runtime";
import { parseGroupField } from "./pivot_helpers";

const { toString, toNumber, toBoolean } = helpers;
const { DEFAULT_LOCALE } = constants;

/**
 * @typedef {import("@spreadsheet").Field} Field
 * @typedef {import("@spreadsheet").SPTableColumn} SPTableColumn
 * @typedef {import("@spreadsheet").SPTableRow} SPTableRow
 */

const UNSUPPORTED_FIELD_TYPES = ["one2many", "binary", "html"];
export const NO_RECORD_AT_THIS_POSITION = Symbol("NO_RECORD_AT_THIS_POSITION");

function isNotSupported(fieldType) {
    return UNSUPPORTED_FIELD_TYPES.includes(fieldType);
}

function throwUnsupportedFieldError(field) {
    throw new EvaluationError(
        sprintf(_t("Field %s is not supported because of its type (%s)"), field.string, field.type)
    );
}

/**
 * @param {import("@spreadsheet").PivotDefinition} definition
 * @param {Record<string, Field | undefined>} [fields]
 *
 * @returns {import("@spreadsheet").WebPivotModelParams}
 */
function definitionForPivotModel(definition, fields) {
    return {
        searchParams: {
            domain: definition.domain,
            context: definition.context,
            groupBy: [],
            orderBy: [],
        },
        metaData: {
            sortedColumn: definition.sortedColumn,
            activeMeasures: definition.measures,
            resModel: definition.model,
            colGroupBys: definition.colGroupBys,
            rowGroupBys: definition.rowGroupBys,
            fieldAttrs: {},
            fields,
        },
        name: definition.name,
    };
}

/**
 * Parses the value defining a pivot group in a PIVOT formula
 * e.g. given the following formula PIVOT("1", "stage_id", "42", "status", "won"),
 * the two group values are "42" and "won".
 * @param {object} field
 * @param {number | boolean | string} groupValue
 * @param {"day" | "week" | "month" | "quarter" | "year" | undefined} aggregateOperator
 * @returns {number | boolean | string}
 */
export function toNormalizedPivotValue(field, groupValue, aggregateOperator) {
    const groupValueString =
        typeof groupValue === "boolean"
            ? toString(groupValue).toLocaleLowerCase()
            : toString(groupValue);
    if (isNotSupported(field.type)) {
        throwUnsupportedFieldError(field);
    }
    // represents a field which is not set (=False server side)
    if (groupValueString === "false") {
        return false;
    }
    switch (field.type) {
        case "datetime":
        case "date":
            return pivotTimeAdapter(aggregateOperator).normalizeFunctionValue(
                groupValueString,
                field
            );
        case "selection":
        case "char":
        case "text":
            return toString(groupValueString);
        case "boolean":
            return toBoolean(groupValueString);
        case "float":
        case "integer":
        case "monetary":
        case "many2one":
        case "many2many":
            return toNumber(groupValueString, DEFAULT_LOCALE);
        default:
            throwUnsupportedFieldError(field);
    }
}

/**
 * This class is an extension of PivotModel with some additional information
 * that we need in spreadsheet (display_name, isUsedInSheet, ...)
 */
export class SpreadsheetPivotModel extends PivotModel {
    /**
     * @param {import("@spreadsheet").WebPivotModelParams} params
     * @param {Object} services
     * @param {import("../data_sources/metadata_repository").MetadataRepository} services.metadataRepository
     */
    setup(params, services) {
        /** This is necessary to ensure the compatibility with the PivotModel from web */
        const p = definitionForPivotModel(params.definition, params.metaData.fields);
        p.searchParams = {
            ...p.searchParams,
            ...params.searchParams,
        };
        super.setup(p);

        this.metadataRepository = services.metadataRepository;

        this.runtime = new OdooPivotDataSource(params.definition, this.metaData.fields);
    }

    getDefinition() {
        return this.runtime.definition;
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
     */
    getPivotCellValue(measure, domain) {
        const { cols, rows } = this._getColsRowsValuesFromDomain(domain);
        const group = JSON.stringify([rows, cols]);
        const values = this.data.measurements[group];
        return (values && values[0][measure]) || "";
    }

    /**
     * Get the value of a field
     *
     * @example
     * getGroupByCellValue("stage_id", 42) // "Won"
     *
     * @param {string} groupFieldString Name of the field
     * @param {string | number} groupValueString Value of the group by
     * @returns {string | number}
     */
    getGroupByCellValue(groupFieldString, groupValueString) {
        if (groupValueString === NO_RECORD_AT_THIS_POSITION) {
            return "";
        }
        const { field, aggregateOperator } = this.parseGroupField(groupFieldString);
        const value = toNormalizedPivotValue(field, groupValueString, aggregateOperator);
        const undef = _t("None");
        if (this._isDateField(field)) {
            const adapter = pivotTimeAdapter(aggregateOperator);
            return adapter.toCellValue(value);
        }
        if (field.relation) {
            const label = this.metadataRepository.getRecordDisplayName(field.relation, value);
            if (!label) {
                return undef;
            }
            return label;
        }
        const label = this.metadataRepository.getLabel(this.metaData.resModel, field.name, value);
        if (!label) {
            return undef;
        }
        return label;
    }

    /**
     * Get the value of the last group by of the function arguments
     * e.g. in `ODOO.PIVOT.HEADER(1, "stage_id", "42", "status", "won")`
     *      the last group value is "won".
     *
     * It can also handle positional arguments.
     * e.g. in `ODOO.PIVOT.HEADER(1, "#stage_id", 1, "#user_id", 1)`
     *      the last group value is the id of the first user of the first stage.
     *
     * @param {(string | number)[]} domainArgs ODOO.PIVOT.HEADER arguments
     */
    getLastPivotGroupValue(domainArgs) {
        const groupFieldString = domainArgs.at(-2);
        if (groupFieldString.startsWith("#")) {
            const { field } = this.parseGroupField(groupFieldString);
            const { cols, rows } = this._getColsRowsValuesFromDomain(domainArgs);
            return this._isCol(field) ? cols.at(-1) : rows.at(-1);
        }
        const groupValueString = domainArgs.at(-1);
        return groupValueString;
    }

    //--------------------------------------------------------------------------
    // Misc
    //--------------------------------------------------------------------------

    /**
     * Get the Odoo domain corresponding to the given domain
     */
    getPivotCellDomain(domain) {
        const { cols, rows } = this._getColsRowsValuesFromDomain(domain);
        const key = JSON.stringify([rows, cols]);
        const domains = this.data.groupDomains[key];
        return domains ? domains[0] : Domain.FALSE.toList();
    }

    getTableStructure() {
        if (this._tableStructure === undefined) {
            // lazy build the structure
            this._tableStructure = this._buildTableStructure();
        }
        return this._tableStructure;
    }

    /**
     * @returns {SpreadsheetPivotTable}
     */
    _buildTableStructure() {
        const cols = this._getSpreadsheetCols();
        const rows = this._getSpreadsheetRows(this.data.rowGroupTree);
        rows.push(rows.shift()); //Put the Total row at the end.
        const measures = this.getDefinition().measures.map((measure) => measure.name);
        const rowTitle = this.getDefinition().rows[0]
            ? this.getDefinition().rows[0].displayName
            : "";
        return new SpreadsheetPivotTable(cols, rows, measures, rowTitle);
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

        const metadataRepository = this.metadataRepository;

        const registerLabels = (tree, groupBys) => {
            const group = tree.root;
            if (!tree.directSubTrees.size) {
                for (let i = 0; i < group.values.length; i++) {
                    const { field } = this.parseGroupField(groupBys[i]);
                    if (!field.relation) {
                        metadataRepository.registerLabel(
                            config.metaData.resModel,
                            field.name,
                            group.values[i],
                            group.labels[i]
                        );
                    } else {
                        metadataRepository.setDisplayName(
                            field.relation,
                            group.values[i],
                            group.labels[i]
                        );
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

    /**
     * Determines if the given field is a date or datetime field.
     *
     * @param {Field} field Field description
     * @private
     * @returns {boolean} True if the type of the field is date or datetime
     */
    _isDateField(field) {
        return ["date", "datetime"].includes(field.type);
    }

    /**
     * @override
     */
    _getGroupValues(group, groupBys) {
        return groupBys.map((gb) => {
            const groupBy = this._normalize(gb);
            const { field, aggregateOperator } = this.parseGroupField(gb);
            if (this._isDateField(field)) {
                return pivotTimeAdapter(aggregateOperator).normalizeServerValue(
                    groupBy,
                    field,
                    group
                );
            }
            return this._sanitizeValue(group[groupBy]);
        });
    }

    /**
     * Check if the given field is used as col group by
     */
    _isCol(field) {
        return this.metaData.fullColGroupBys
            .map(this.parseGroupField)
            .map(({ field }) => field.name)
            .includes(field.name);
    }

    /**
     * Check if the given field is used as row group by
     */
    _isRow(field) {
        return this.metaData.fullRowGroupBys
            .map(this.parseGroupField)
            .map(({ field }) => field.name)
            .includes(field.name);
    }

    /**
     * Get the value of a field-value for a positional group by
     *
     * @param {object} field Field of the group by
     * @param {unknown} groupValueString Value of the group by
     * @param {(number | boolean | string)[]} rows Values for the previous row group bys
     * @param {(number | boolean | string)[]} cols Values for the previous col group bys
     *
     * @private
     * @returns {number | boolean | string}
     */
    _parsePivotFormulaWithPosition(field, groupValueString, cols, rows) {
        const position = toNumber(groupValueString, DEFAULT_LOCALE) - 1;
        let tree;
        if (this._isCol(field)) {
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
     * @param {(number | boolean | string)[]} domain Domain
     *
     * @private
     */
    _getColsRowsValuesFromDomain(domain) {
        const rows = [];
        const cols = [];
        let i = 0;
        while (i < domain.length) {
            const groupFieldString = domain[i];
            const groupValue = domain[i + 1];
            const { field, isPositional, aggregateOperator } =
                this.parseGroupField(groupFieldString);
            let value;
            if (isPositional) {
                value = this._parsePivotFormulaWithPosition(field, groupValue, cols, rows);
            } else {
                value = toNormalizedPivotValue(field, groupValue, aggregateOperator);
            }
            if (this._isCol(field)) {
                cols.push(value);
            } else if (this._isRow(field)) {
                rows.push(value);
            }
            i += 2;
        }
        return { rows, cols };
    }

    /**
     * Get the row structure
     * @returns {SPTableRow[]}
     */
    _getSpreadsheetRows(tree) {
        /**@type {SPTableRow[]}*/
        let rows = [];
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
            rows = rows.concat(this._getSpreadsheetRows(subTree));
        });
        return rows;
    }

    /**
     * Get the col structure
     * @returns {SPTableColumn[][]}
     */
    _getSpreadsheetCols() {
        const colGroupBys = this.metaData.fullColGroupBys;
        const height = colGroupBys.length;
        const measureCount = this.getDefinition().measures.length;
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
                this.getDefinition().measures.forEach((measure) => {
                    const measureCell = {
                        fields: [...cell.fields, "measure"],
                        values: [...cell.values, measure.name],
                        width: 1,
                    };
                    measureRow.push(measureCell);
                });
            });
        }
        this.getDefinition().measures.forEach((measure) => {
            const measureCell = {
                fields: ["measure"],
                values: [measure.name],
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
            width: this.getDefinition().measures.length,
        });

        return headers;
    }
}
