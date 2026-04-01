import {
    TABLE_ATTRIBUTES,
    TABLE_STYLES,
} from "@mail/views/web/fields/html_mail_field/convert_inline";

const tableAttributesString = Object.keys(TABLE_ATTRIBUTES)
    .map((key) => `${key}="${TABLE_ATTRIBUTES[key]}"`)
    .join(" ");
const tableStylesString = Object.keys(TABLE_STYLES)
    .map((key) => `${key}: ${TABLE_STYLES[key]};`)
    .join(" ");
/**
 * Take a matrix representing a grid and return an HTML string of the Bootstrap
 * grid. The matrix is an array of rows, with each row being an array of cells.
 * Each cell can be represented either by a 0 < number < 13 (col-#) or a falsy
 * value (col). Each cell has its coordinates `(row index, column index)` as
 * text content.
 * Eg: [                        // <div class="container">
 *      [                       //     <div class="row">
 *          1,                  //         <div class="col-1">(0, 0)</div>
 *          11,                 //         <div class="col-11">(0, 1)</div>
 *      ],                      //     </div>
 *      [                       //     <div class="row">
 *          false,              //         <div class="col">(1, 0)</div>
 *      ],                      //     </div>
 * ]                            // </div>
 *
 * @param {Array<Array<Number|null>>} matrix
 * @returns {string}
 */
export function getGridHtml(matrix) {
    return (
        `<div class="container">` +
        matrix
            .map(
                (row, iRow) =>
                    `<div class="row">` +
                    row
                        .map(
                            (col, iCol) =>
                                `<div class="${
                                    col ? "col-" + col : "col"
                                }">(${iRow}, ${iCol})</div>`
                        )
                        .join("") +
                    `</div>`
            )
            .join("") +
        `</div>`
    );
}
export function getTdHtml(colspan, text, containerWidth) {
    const style = containerWidth
        ? ` style="max-width: ${Math.round(((containerWidth * colspan) / 12) * 100) / 100}px;"`
        : "";
    return `<td colspan="${colspan}"${style}>${text}</td>`;
}
/**
 * Take a matrix representing a table and return an HTML string of the table.
 * The matrix is an array of rows, with each row being an array of cells. Each
 * cell is represented by a tuple of numbers [colspan, width (in percent)]. A
 * cell can have a string as third value to represent its text content. The
 * default text content of each cell is its coordinates `(row index, column
 * index)`. If the cell has a number as third value, it will be used as the
 * max-width of the cell (in pixels).
 * Eg: [                        // <table> (note: extra attrs and styles apply)
 *      [                       //   <tr>
 *          [1, 8],             //     <td colspan="1" width="8%">(0, 0)</td>
 *          [11, 92]            //     <td colspan="11" width="92%">(0, 1)</td>
 *      ],                      //   </tr>
 *      [                       //   <tr>
 *          [2, 17, 'A'],       //     <td colspan="2" width="17%">A</td>
 *          [10, 83],           //     <td colspan="10" width="83%">(1, 1)</td>
 *      ],                      //   </tr>
 * ]                            // </table>
 *
 * @param {Array<Array<Array<[Number, Number, string?, number?]>>>} matrix
 * @param {Number} [containerWidth]
 * @returns {string}
 */
export function getTableHtml(matrix, containerWidth) {
    return (
        `<table ${tableAttributesString} style="width: 100% !important; ${tableStylesString}">` +
        matrix
            .map(
                (row, iRow) =>
                    `<tr>` +
                    row
                        .map((col, iCol) =>
                            getTdHtml(
                                col[0],
                                typeof col[2] === "string" ? col[2] : `(${iRow}, ${iCol})`,
                                containerWidth
                            )
                        )
                        .join("") +
                    `</tr>`
            )
            .join("") +
        `</table>`
    );
}
/**
 * Take a number of rows and a number of columns (or number of columns per
 * individual row) and return an HTML string of the corresponding grid. Every
 * column is a regular Bootstrap "col" (no col-#).
 * Eg: [2, 3] <=> getGridHtml([[false, false, false], [false, false, false]])
 * Eg: [2, [2, 1]] <=> getGridHtml([[false, false], [false]])
 *
 * @see getGridHtml
 * @param {Number} nRows
 * @param {Number|Number[]} nCols
 * @returns {string}
 */
export function getRegularGridHtml(nRows, nCols) {
    const matrix = new Array(nRows)
        .fill()
        .map((_, iRow) => new Array(Array.isArray(nCols) ? nCols[iRow] : nCols).fill());
    return getGridHtml(matrix);
}
/**
 * Take a number of rows, a number of columns (or number of columns per
 * individual row), a colspan (or colspan per individual row) and a width (or
 * width per individual row, in percent), and return an HTML string of the
 * corresponding table. Every cell in a row has the same colspan/width.
 * Eg: [2, 2, 6, 50] <=> getTableHtml([[[6, 50], [6, 50]], [[6, 50], [6, 50]]])
 * Eg: [2, [2, 1], [6, 12], [50, 100]] <=> getTableHtml([[[6, 50], [6, 50]], [[12, 100]]])
 *
 * @see getTableHtml
 * @param {Number} nRows
 * @param {Number|Number[]} nCols
 * @param {Number|Number[]} colspan
 * @param {Number|Number[]} width
 * @param {Number} containerWidth
 * @returns {string}
 */
export function getRegularTableHtml(nRows, nCols, colspan, width, containerWidth) {
    const matrix = new Array(nRows)
        .fill()
        .map((_, iRow) =>
            new Array(Array.isArray(nCols) ? nCols[iRow] : nCols)
                .fill()
                .map(() => [
                    Array.isArray(colspan) ? colspan[iRow] : colspan,
                    Array.isArray(width) ? width[iRow] : width,
                ])
        );
    return getTableHtml(matrix, containerWidth);
}
