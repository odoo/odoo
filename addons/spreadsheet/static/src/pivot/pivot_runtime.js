/** @odoo-module */
// @ts-check

import { _t } from "@web/core/l10n/translation";
import { PERIODS, parseGroupField } from "@spreadsheet/pivot/pivot_helpers";

/**
 * @typedef {import("@spreadsheet").Fields} Fields
 * @typedef {import("@spreadsheet").CommonPivotDefinition} CommonPivotDefinition
 * @typedef {import("@spreadsheet").SortedColumn} SortedColumn
 */

/**
 * Represent a pivot runtime definition. A pivot runtime definition is a pivot
 * definition that has been enriched to include the display name of its attributes
 * (measures, columns, rows).
 */
export class PivotRuntimeDefinition {
    /**
     *
     * @param {CommonPivotDefinition} definition
     * @param {Fields} fields
     */
    constructor(definition, fields) {
        /** @type {string} */
        this._name = definition.name;
        /** @type {SortedColumn} */
        this._sortedColumn = definition.sortedColumn;
        /** @type {Array<PivotMeasure>} */
        this._measures = definition.measures.map((name) => new PivotMeasure(fields, name));
        /** @type {Array<PivotDimension>} */
        this._columns = definition.colGroupBys.map((name) => new PivotDimension(fields, name));
        /** @type {Array<PivotDimension>} */
        this._rows = definition.rowGroupBys.map((name) => new PivotDimension(fields, name));
    }

    get name() {
        return this._name;
    }

    get sortedColumn() {
        return this._sortedColumn;
    }

    get measures() {
        return this._measures;
    }

    get columns() {
        return this._columns;
    }

    get rows() {
        return this._rows;
    }
}

/**
 * Represent a measure in a pivot. A measure is a field that is aggregated.
 */
export class PivotMeasure {
    /**
     * @param {Fields} fields All fields of the model
     * @param {string} measureName Name of the measure
     */
    constructor(fields, measureName) {
        this._fields = fields;
        this._measureName = measureName;
    }

    /**
     * Get the display name of the measure
     * e.g. "__count" -> "Count", "amount_total" -> "Total Amount"
     */
    get displayName() {
        return this._measureName === "__count"
            ? _t("Count")
            : this._fields[this._measureName].string;
    }

    /**
     * Get the name of the measure, as it is stored in the pivot formula
     */
    get name() {
        return this._measureName;
    }
}

/**
 * Represent a dimension in a pivot. A dimension is a field that is grouped by.
 * e.g. "stage_id", "create_date:month"
 */
export class PivotDimension {
    /**
     * @param {Fields} fields All fields of the model
     * @param {string} name Name of the dimension
     */
    constructor(fields, name) {
        this._fields = fields;
        const { field, aggregateOperator } = parseGroupField(fields, name);
        this._field = field;
        this._aggregateOperator = aggregateOperator;
        this._name = name;
    }

    /**
     * Get the display name of the dimension
     * e.g. "stage_id" -> "Stage", "create_date:month" -> "Create Date (Month)"
     */
    get displayName() {
        return (
            this._field.string +
            (this._aggregateOperator ? ` (${PERIODS[this._aggregateOperator]})` : "")
        );
    }

    /**
     * Get the name of the dimension, as it is stored in the pivot formula
     * e.g. "stage_id", "create_date:month"
     */
    get name() {
        return this._name;
    }

    /**
     * Get the name of the field of the dimension
     * e.g. "stage_id" -> "stage_id", "create_date:month" -> "create_date"
     */
    get fieldName() {
        return this._field.name;
    }

    /**
     * Get the aggregate operator of the dimension
     * e.g. "stage_id" -> undefined, "create_date:month" -> "month"
     */
    get aggregateOperator() {
        return this._aggregateOperator;
    }

    /**
     * Get the type of the field of the dimension
     * e.g. "stage_id" -> "many2one", "create_date:month" -> "date"
     */
    get type() {
        return this._field.type;
    }
}
