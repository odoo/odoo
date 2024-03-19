/** @odoo-module */
// @ts-check

import { _t } from "@web/core/l10n/translation";

/**
 * @typedef {import("@spreadsheet").Fields} Fields
 * @typedef {import("@spreadsheet").CommonPivotDefinition} CommonPivotDefinition
 * @typedef {import("@spreadsheet").SortedColumn} SortedColumn
 * @typedef {import("@spreadsheet").PivotMeasureDefinition} PivotMeasureDefinition
 * @typedef {import("@spreadsheet").PivotMeasure} PivotMeasure
 * @typedef {import("@spreadsheet").PivotDimensionDefinition} PivotDimensionDefinition
 * @typedef {import("@spreadsheet").PivotDimension} PivotDimension
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
        /** @type {SortedColumn} */
        this._sortedColumn = definition.sortedColumn;
        /** @type {Array<PivotMeasure>} */
        this._measures = definition.measures.map((measure) => createMeasure(fields, measure));
        /** @type {Array<PivotDimension>} */
        this._columns = definition.columns.map((dimension) =>
            createPivotDimension(fields, dimension)
        );
        /** @type {Array<PivotDimension>} */
        this._rows = definition.rows.map((dimension) => createPivotDimension(fields, dimension));
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
 * @param {Fields} fields
 * @param {PivotMeasureDefinition} measure
 * @returns {PivotMeasure}
 */
function createMeasure(fields, measure) {
    const name = measure.name;
    const aggregator = measure.aggregator || fields[name]?.aggregator;
    return {
        nameWithAggregator: name + (aggregator ? `:${aggregator}` : ""),
        /**
         * Display name of the measure
         * e.g. "__count" -> "Count", "amount_total" -> "Total Amount"
         */
        displayName: name === "__count" ? _t("Count") : fields[name].string,
        /**
         * Get the name of the measure, as it is stored in the pivot formula
         */
        name,
        /**
         * Get the aggregator of the measure
         */
        aggregator,
        /**
         * Get the type of the measure field
         * e.g. "stage_id" -> "many2one", "create_date:month" -> "date"
         */
        type: name === "__count" ? "integer" : fields[name].type,
    };
}

/**
 * @param {Fields} fields
 * @param {PivotDimensionDefinition} dimension
 * @returns {PivotDimension}
 */
function createPivotDimension(fields, dimension) {
    const field = fields[dimension.name];
    return {
        /**
         * Get the display name of the dimension
         * e.g. "stage_id" -> "Stage", "create_date:month" -> "Create Date"
         */
        displayName: field.string,

        /**
         * Get the name of the dimension, as it is stored in the pivot formula
         * e.g. "stage_id", "create_date:month"
         */
        nameWithGranularity:
            dimension.name + (dimension.granularity ? `:${dimension.granularity}` : ""),

        /**
         * Get the name of the field of the dimension
         * e.g. "stage_id" -> "stage_id", "create_date:month" -> "create_date"
         */
        name: dimension.name,

        /**
         * Get the aggregate operator of the dimension
         * e.g. "stage_id" -> undefined, "create_date:month" -> "month"
         */
        granularity: dimension.granularity,

        /**
         * Get the type of the field of the dimension
         * e.g. "stage_id" -> "many2one", "create_date:month" -> "date"
         */
        type: field.type,

        order: dimension.order,
    };
}
