/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { PERIODS, parseGroupField } from "@spreadsheet/pivot/pivot_helpers";

class PivotRuntime {
    constructor(rawDefinition, fields) {
        this._sortedColumn = rawDefinition.sortedColumn;

        this._measures = rawDefinition.measures.map((name) => new PivotMeasure(fields, name));
        this._columns = rawDefinition.colGroupBys.map((name) => new PivotDimension(fields, name));
        this._rows = rawDefinition.rowGroupBys.map((name) => new PivotDimension(fields, name));
    }

    get definition() {
        return {
            sortedColumn: this._sortedColumn,
            measures: this._measures,
            columns: this._columns,
            rows: this._rows,
        };
    }
}

export class OdooPivotDataSource extends PivotRuntime {
    /**
     * @param {import("@spreadsheet").PivotDefinition} rawDefinition
     * @param {Record<string, Field | undefined>} fields All fields of the model
     */
    constructor(rawDefinition, fields) {
        super(rawDefinition, fields);
        this._domain = rawDefinition.domain;
        this._context = rawDefinition.context;
        this._model = rawDefinition.model;
    }

    get definition() {
        return {
            ...super.definition,
            domain: this._domain,
            context: this._context,
            model: this._model,
        };
    }
}

/**
 * Represent a measure in a pivot. A measure is a field that is aggregated.
 */
class PivotMeasure {
    /**
     * @param {Record<string, Field | undefined>} fields All fields of the model
     * @param {string} measureName Name of the measure
     */
    constructor(fields, measureName) {
        this._fieldsGet = fields;
        this._measureName = measureName;
    }

    /**
     * Get the display name of the measure
     * e.g. "__count" -> "Count", "amount_total" -> "Total Amount"
     */
    get displayName() {
        return this._measureName === "__count"
            ? _t("Count")
            : this._fieldsGet[this._measureName].string;
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
class PivotDimension {
    /**
     * @param {Record<string, Field | undefined>} fields All fields of the model
     * @param {string} name Name of the dimension
     */
    constructor(fields, name) {
        this._fieldsGet = fields;
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
