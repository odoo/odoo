/** @odoo-module */

/**
 * @typedef {Object} Column
 * @property {string[]} fields
 * @property {string[]} values
 * @property {number} width
 *
 * @typedef {Object} Row
 * @property {string[]} fields
 * @property {string[]} values
 * @property {number} intend
 *
 * @typedef {Object} SpreadsheetTableData
 * @property {Column[][]} cols
 * @property {Row[]} rows
 * @property {string[]} measures
 */

/**
 * Class used to ease the construction of a pivot table.
 * Let's consider the following example, with:
 * - columns groupBy: [sales_team, create_date]
 * - rows groupBy: [continent, city]
 * - measures: [revenues]
 * _____________________________________________________________________________________|   ----|
 * |                |   Sale Team 1             |  Sale Team 2            |             |       |
 * |                |___________________________|_________________________|_____________|       |
 * |                |   May 2020   | June 2020  |  May 2020  | June 2020  |   Total     |       |<---- `cols`
 * |                |______________|____________|____________|____________|_____________|       |   ----|
 * |                |   Revenues   |  Revenues  |  Revenues  |  Revenues  |   Revenues  |       |       |<--- `measureRow`
 * |________________|______________|____________|____________|____________|_____________|   ----|   ----|
 * |Europe          |     25       |     35     |     40     |     30     |     65      |   ----|
 * |    Brussels    |      0       |     15     |     30     |     30     |     30      |       |
 * |    Paris       |     25       |     20     |     10     |     0      |     35      |       |
 * |North America   |     60       |     75     |            |            |     60      |       |<---- `body`
 * |    Washington  |     60       |     75     |            |            |     60      |       |
 * |Total           |     85       |     110    |     40     |     30     |     125     |       |
 * |________________|______________|____________|____________|____________|_____________|   ----|
 *
 * |                |
 * |----------------|
 *         |
 *         |
 *       `rows`
 *
 * `rows` is an array of cells, each cells contains the indent level, the fields used for the group by and the values for theses fields.
 * For example:
 *   `Europe`: { indent: 1, fields: ["continent"], values: ["id_of_Europe"]}
 *   `Brussels`: { indent: 2, fields: ["continent", "city"], values: ["id_of_Europe", "id_of_Brussels"]}
 *   `Total`: { indent: 0, fields: [], values: []}
 *
 * `columns` is an double array, first by row and then by cell. So, in this example, it looks like:
 *   [[row1], [row2], [measureRow]]
 *   Each cell of a column's row contains the width (span) of the cells, the fields used for the group by and the values for theses fields.
 * For example:
 *   `Sale Team 1`: { width: 2, fields: ["sales_team"], values: ["id_of_SaleTeam1"]}
 *   `May 2020` (the one under Sale Team 2): { width: 1, fields: ["sales_team", "create_date"], values: ["id_of_SaleTeam2", "May 2020"]}
 *   `Revenues` (the one under Total): { width: 1, fields: ["measure"], values: ["revenues"]}
 *
 */
export class SpreadsheetPivotTable {
    /**
     * @param {Column[][]} cols
     * @param {Row[]} rows
     * @param {string[]} measures
     */
    constructor(cols, rows, measures) {
        this._cols = cols;
        this._rows = rows;
        this._measures = measures;
    }

    /**
     * @returns {number}
     */
    getNumberOfMeasures() {
        return this._measures.length;
    }

    /**
     * @returns {Column[][]}
     */
    getColHeaders() {
        return this._cols;
    }

    /**
     * Get the last row of the columns (i.e. the one with the measures)
     * @returns {Column[]}
     */
    getMeasureHeaders() {
        return this._cols[this._cols.length - 1];
    }

    /**
     * Get the number of columns leafs (i.e. the number of the last row of columns)
     * @returns {number}
     */
    getColWidth() {
        return this._cols[this._cols.length - 1].length;
    }

    /**
     * Get the number of row in each columns
     * @return {number}
     */
    getColHeight() {
        return this._cols.length;
    }

    /**
     * @returns {Row[]}
     */
    getRowHeaders() {
        return this._rows;
    }

    /**
     * Get the number of rows
     *
     * @returns {number}
     */
    getRowHeight() {
        return this._rows.length;
    }

    /**
     * Get the index of the cell in the measure row (i.e. the last one) which
     * correspond to the given values
     *
     * @returns {number}
     */
    getColMeasureIndex(values) {
        const vals = JSON.stringify(values);
        const maxLength = Math.max(...this._cols.map((col) => col.length));
        for (let i = 0; i < maxLength; i++) {
            const cellValues = this._cols.map((col) => JSON.stringify((col[i] || {}).values));
            if (cellValues.includes(vals)) {
                return i;
            }
        }
        return -1;
    }

    /**
     *
     * @param {number} colIndex
     * @param {number} rowIndex
     * @returns {Column}
     */
    getNextColCell(colIndex, rowIndex) {
        return this._cols[rowIndex][colIndex];
    }

    getRowIndex(values) {
        const vals = JSON.stringify(values);
        return this._rows.findIndex(
            (cell) => JSON.stringify(cell.values.map((val) => val.toString())) === vals
        );
    }

    getCellFromMeasureRowAtIndex(index) {
        return this.getMeasureHeaders()[index];
    }

    getCellsFromRowAtIndex(index) {
        return this._rows[index];
    }

    /**
     * @returns {SpreadsheetTableData}
     */
    export() {
        return {
            cols: this._cols,
            rows: this._rows,
            measures: this._measures,
        };
    }
}
