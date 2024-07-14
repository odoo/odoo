/** @odoo-module */

import { Dialog } from "@web/core/dialog/dialog";
import { PivotDialogTable } from "./spreadsheet_pivot_dialog_table";

import * as spreadsheet from "@odoo/o-spreadsheet";

import { makePivotFormula } from "@spreadsheet/pivot/pivot_helpers";

import { Component, useState } from "@odoo/owl";
const formatValue = spreadsheet.helpers.formatValue;

/**
 * @typedef {Object} PivotDialogColumn
 * @property {string} formula Pivot formula
 * @property {string} value Pivot value of the formula
 * @property {number} span Size of col-span
 * @property {boolean} isMissing True if the value is missing from the sheet
 * @property {string} style Style of the column
 */

/**
 * @typedef {Object} PivotDialogRow
 * @property {Array<string>} args Args of the pivot formula
 * @property {string} formula Pivot formula
 * @property {string} value Pivot value of the formula
 * @property {boolean} isMissing True if the value is missing from the sheet
 * @property {string} style Style of the column
 */

/**
 * @typedef {Object} PivotDialogValue
 * @property {Object} args
 * @property {string} args.formula Pivot formula
 * @property {string} args.value Pivot value of the formula
 * @property {boolean} isMissing True if the value is missing from the sheet
 */

export class PivotDialog extends Component {
    setup() {
        this.state = useState({
            showMissingValuesOnly: false,
        });
        this.dataSource = this.props.getters.getPivotDataSource(this.props.pivotId);

        const table = this.dataSource.getTableStructure();
        const id = this.props.pivotId;
        this.data = {
            columns: this._buildColHeaders(id, table),
            rows: this._buildRowHeaders(id, table),
            values: this._buildValues(id, table),
        };
    }

    _onCellClicked(detail) {
        this.props.insertPivotValueCallback(detail.formula);
        this.props.close();
    }

    // ---------------------------------------------------------------------
    // Missing values building
    // ---------------------------------------------------------------------

    /**
     * Retrieve the data to display in the Pivot Table
     * In the case when showMissingValuesOnly is false, the returned value
     * is the complete data
     * In the case when showMissingValuesOnly is true, the returned value is
     * the data which contains only missing values in the rows and cols. In
     * the rows, we also return the parent rows of rows which contains missing
     * values, to give context to the user.
     *
     * @returns {Object} { columns, rows, values }
     */
    getTableData() {
        if (!this.state.showMissingValuesOnly) {
            return this.data;
        }
        const colIndexes = this._getColumnsIndexes();
        const rowIndexes = this._getRowsIndexes();
        const columns = this._buildColumnsMissing(colIndexes);
        const rows = this._buildRowsMissing(rowIndexes);
        const values = this._buildValuesMissing(colIndexes, rowIndexes);
        return { columns, rows, values };
    }

    getRowIndex(groupValues) {
        const stringifiedValues = JSON.stringify(groupValues);
        return this._rows.findIndex((values) => JSON.stringify(values) === stringifiedValues);
    }

    /**
     * Retrieve the parents of the given row
     * ex:
     *  Australia
     *    January
     *    February
     * The parent of "January" is "Australia"
     *
     * @private
     * @param {number} index Index of the row
     * @returns {Array<number>}
     */
    _addRecursiveRow(index) {
        const rows = this.dataSource.getTableStructure().getRowHeaders();
        const row = [...rows[index].values];
        if (row.length <= 1) {
            return [index];
        }
        row.pop();
        const parentRowIndex = rows.findIndex(
            (r) => JSON.stringify(r.values) === JSON.stringify(row)
        );
        return [index].concat(this._addRecursiveRow(parentRowIndex));
    }
    /**
     * Create the columns to be used, based on the indexes of the columns in
     * which a missing value is present
     *
     * @private
     * @param {Array<number>} indexes Indexes of columns with a missing value
     * @returns {Array<Array<PivotDialogColumn>>}
     */
    _buildColumnsMissing(indexes) {
        // columnsMap explode the columns in an array of array of the same
        // size with the index of each column, repeated 'span' times.
        // ex:
        //  | A     | B |
        //  | 1 | 2 | 3 |
        // => [
        //      [0, 0, 1]
        //      [0, 1, 2]
        //    ]
        const columnsMap = [];
        for (const column of this.data.columns) {
            const columnMap = [];
            for (const index in column) {
                for (let i = 0; i < column[index].span; i++) {
                    columnMap.push(index);
                }
            }
            columnsMap.push(columnMap);
        }
        // Remove the columns that are not present in indexes
        for (let i = columnsMap[columnsMap.length - 1].length; i >= 0; i--) {
            if (!indexes.includes(i)) {
                for (const columnMap of columnsMap) {
                    columnMap.splice(i, 1);
                }
            }
        }
        // Build the columns
        const columns = [];
        for (const mapIndex in columnsMap) {
            const column = [];
            let index = undefined;
            let span = 1;
            for (let i = 0; i < columnsMap[mapIndex].length; i++) {
                if (index !== columnsMap[mapIndex][i]) {
                    if (index) {
                        column.push(
                            Object.assign({}, this.data.columns[mapIndex][index], { span })
                        );
                    }
                    index = columnsMap[mapIndex][i];
                    span = 1;
                } else {
                    span++;
                }
            }
            if (index) {
                column.push(Object.assign({}, this.data.columns[mapIndex][index], { span }));
            }
            columns.push(column);
        }
        return columns;
    }
    /**
     * Create the rows to be used, based on the indexes of the rows in
     * which a missing value is present.
     *
     * @private
     * @param {Array<number>} indexes Indexes of rows with a missing value
     * @returns {Array<PivotDialogRow>}
     */
    _buildRowsMissing(indexes) {
        return indexes.map((index) => this.data.rows[index]);
    }
    /**
     * Create the value to be used, based on the indexes of the columns and
     * rows in which a missing value is present.
     *
     * @private
     * @param {Array<number>} colIndexes Indexes of columns with a missing value
     * @param {Array<number>} rowIndexes Indexes of rows with a missing value
     * @returns {Array<PivotDialogValue>}
     */
    _buildValuesMissing(colIndexes, rowIndexes) {
        const values = colIndexes.map(() => []);
        for (const row of rowIndexes) {
            for (const col in colIndexes) {
                values[col].push(this.data.values[colIndexes[col]][row]);
            }
        }
        return values;
    }
    /**
     * Get the indexes of the columns in which a missing value is present
     * @private
     * @returns {Array<number>}
     */
    _getColumnsIndexes() {
        const indexes = new Set();
        for (let i = 0; i < this.data.columns.length; i++) {
            const exploded = [];
            for (let y = 0; y < this.data.columns[i].length; y++) {
                for (let x = 0; x < this.data.columns[i][y].span; x++) {
                    exploded.push(this.data.columns[i][y]);
                }
            }
            for (let y = 0; y < exploded.length; y++) {
                if (exploded[y].isMissing) {
                    indexes.add(y);
                }
            }
        }
        for (let i = 0; i < this.data.columns[this.data.columns.length - 1].length; i++) {
            const values = this.data.values[i];
            if (values.find((x) => x.isMissing)) {
                indexes.add(i);
            }
        }
        return Array.from(indexes).sort((a, b) => a - b);
    }
    /**
     * Get the indexes of the rows in which a missing value is present
     * @private
     * @returns {Array<number>}
     */
    _getRowsIndexes() {
        const rowIndexes = new Set();
        for (let i = 0; i < this.data.rows.length; i++) {
            if (this.data.rows[i].isMissing) {
                rowIndexes.add(i);
            }
            for (const col of this.data.values) {
                if (col[i].isMissing) {
                    this._addRecursiveRow(i).forEach((x) => rowIndexes.add(x));
                }
            }
        }
        return Array.from(rowIndexes).sort((a, b) => a - b);
    }

    // ---------------------------------------------------------------------
    // Data table creation
    // ---------------------------------------------------------------------

    /**
     * Create the columns headers of the Pivot
     *
     * @param {string} id Pivot Id
     * @param {SpreadsheetPivotTable} table
     *
     * @private
     * @returns {Array<Array<PivotDialogColumn>>}
     */
    _buildColHeaders(id, table) {
        const headers = [];
        for (const row of table.getColHeaders()) {
            const current = [];
            for (const cell of row) {
                const domain = [];
                for (let i = 0; i < cell.fields.length; i++) {
                    domain.push(cell.fields[i]);
                    domain.push(cell.values[i]);
                }
                current.push({
                    formula: makePivotFormula("ODOO.PIVOT.HEADER", [id, ...domain]),
                    value: this.props.getters.getPivotHeaderFormattedValue(id, domain),
                    span: cell.width,
                    isMissing: !this.dataSource.isUsedHeader(domain),
                });
            }
            headers.push(current);
        }
        const last = headers[headers.length - 1];
        headers[headers.length - 1] = last.map((cell) => {
            if (!cell.isMissing) {
                cell.style = "color: #756f6f;";
            }
            return cell;
        });
        return headers;
    }
    /**
     * Create the row of the pivot table
     *
     * @param {string} id Pivot Id
     * @param {SpreadsheetPivotTable} table
     *
     * @private
     * @returns {Array<PivotDialogRow>}
     */
    _buildRowHeaders(id, table) {
        const headers = [];
        for (const row of table.getRowHeaders()) {
            const domain = [];
            for (let i = 0; i < row.fields.length; i++) {
                domain.push(row.fields[i]);
                domain.push(row.values[i]);
            }
            const cell = {
                args: domain,
                formula: makePivotFormula("ODOO.PIVOT.HEADER", [id, ...domain]),
                value: this.props.getters.getPivotHeaderFormattedValue(id, domain),
                isMissing: !this.dataSource.isUsedHeader(domain),
            };
            if (row.indent > 1) {
                cell.style = `padding-left: ${row.indent - 1 * 10}px`;
            }
            headers.push(cell);
        }
        return headers;
    }
    /**
     * Build the values of the pivot table
     *
     * @param {string} id Pivot Id
     * @param {SpreadsheetPivotTable} table
     *
     * @private
     * @returns {Array<PivotDialogValue>}
     */
    _buildValues(id, table) {
        const values = [];
        for (const col of table.getMeasureHeaders()) {
            const current = [];
            const measure = col.values[col.values.length - 1];
            for (const row of table.getRowHeaders()) {
                const domain = [];
                for (let i = 0; i < row.fields.length; i++) {
                    domain.push(row.fields[i]);
                    domain.push(row.values[i]);
                }
                for (let i = 0; i < col.fields.length - 1; i++) {
                    domain.push(col.fields[i]);
                    domain.push(col.values[i]);
                }
                const value = this.dataSource.getPivotCellValue(measure, domain);
                const locale = this.props.getters.getLocale();
                current.push({
                    args: {
                        formula: makePivotFormula("ODOO.PIVOT", [id, measure, ...domain]),
                        value: !value ? "" : formatValue(value, { locale }),
                    },
                    isMissing: !this.dataSource.isUsedValue(domain, measure),
                });
            }
            values.push(current);
        }
        return values;
    }
}

PivotDialog.template = "spreadsheet_edition.PivotDialog";
PivotDialog.components = { Dialog, PivotDialogTable };
PivotDialog.props = {
    title: String,
    pivotId: String,
    insertPivotValueCallback: Function,
    getters: Object,
    close: Function, // prop added by Dialog service
};
