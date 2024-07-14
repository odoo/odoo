/** @odoo-module **/

import * as spreadsheet from "@odoo/o-spreadsheet";
import { CommandResult } from "@spreadsheet/o_spreadsheet/cancelled_reason";
import { pivotFormulaRegex } from "@spreadsheet/pivot/pivot_helpers";
const { parse, astToFormula } = spreadsheet;
const { featurePluginRegistry } = spreadsheet.registries;

/**
 * @typedef {Object} Range
 */

export class PivotTemplatePlugin extends spreadsheet.UIPlugin {
    allowDispatch(cmd) {
        switch (cmd.type) {
            case "CONVERT_PIVOT_TO_TEMPLATE":
            case "CONVERT_PIVOT_FROM_TEMPLATE": {
                for (const pivotId of this.getters.getPivotIds()) {
                    if (!this.getters.getPivotDataSource(pivotId).isReady()) {
                        return CommandResult.PivotCacheNotLoaded;
                    }
                }
                break;
            }
        }
        return CommandResult.Success;
    }

    /**
     * Handle a spreadsheet command
     *
     * @param {Object} cmd Command
     */
    handle(cmd) {
        switch (cmd.type) {
            case "CONVERT_PIVOT_TO_TEMPLATE":
                this._convertFormulas(
                    this._getCells(pivotFormulaRegex),
                    this._absoluteToRelative.bind(this),
                    this.getters.getPivotIds().map(this.getters.getPivotDefinition)
                );
                break;
            case "CONVERT_PIVOT_FROM_TEMPLATE":
                this._convertFormulas(
                    this._getCells(pivotFormulaRegex),
                    this._relativeToAbsolute.bind(this),
                    this.getters.getPivotIds().map(this.getters.getPivotDefinition)
                );
                this._removeInvalidPivotRows();
                break;
        }
    }

    /**
     * Applies a transformation function to all given formula cells.
     * The transformation function takes as fist parameter the cell AST and should
     * return a modified AST.
     * Any additional parameter is forwarded to the transformation function.
     *
     * @param {Array<Object>} cells
     * @param {Function} convertFunction
     * @param {...any} args
     */
    _convertFormulas(cells, convertFunction, ...args) {
        cells.forEach((cell) => {
            if (cell.isFormula) {
                const { col, row, sheetId } = this.getters.getCellPosition(cell.id);
                const ast = convertFunction(parse(cell.content), ...args);
                if (ast) {
                    const content = `=${astToFormula(ast)}`;
                    this.dispatch("UPDATE_CELL", {
                        content,
                        sheetId,
                        col,
                        row,
                    });
                } else {
                    this.dispatch("CLEAR_CELL", {
                        sheetId,
                        col,
                        row,
                    });
                }
            }
        });
    }

    /**
     * Return all formula cells matching a given regular expression.
     *
     * @param {RegExp} regex
     * @returns {Array<Object>}
     */
    _getCells(regex) {
        return this.getters
            .getSheetIds()
            .map((sheetId) =>
                Object.values(this.getters.getCells(sheetId)).filter(
                    (cell) => cell.isFormula && regex.test(cell.content)
                )
            )
            .flat();
    }

    /**
     * return AST from an relative PIVOT ast to a absolute PIVOT ast (sheet -> template)
     * *
     * relative PIVOTS formulas use the position while Absolute PIVOT
     * formulas use hardcoded ids
     *
     * e.g.
     * The following relative formula
     *      `PIVOT("1","probability","product_id",PIVOT.POSITION("1","product_id",0),"bar","110")`
     * is converted to
     *      `PIVOT("1","probability","product_id","37","bar","110")`
     *
     * @param {Object} ast
     * @returns {Object}
     */
    _relativeToAbsolute(ast) {
        switch (ast.type) {
            case "FUNCALL":
                switch (ast.value) {
                    case "ODOO.PIVOT.POSITION":
                        return this._pivotPositionToAbsolute(ast);
                    default:
                        return Object.assign({}, ast, {
                            args: ast.args.map((child) => this._relativeToAbsolute(child)),
                        });
                }
            case "UNARY_OPERATION":
                return Object.assign({}, ast, {
                    operand: this._relativeToAbsolute(ast.operand),
                });
            case "BIN_OPERATION":
                return Object.assign({}, ast, {
                    right: this._relativeToAbsolute(ast.right),
                    left: this._relativeToAbsolute(ast.left),
                });
        }
        return ast;
    }

    /**
     * return AST from an absolute PIVOT ast to a relative ast.
     *
     * Absolute PIVOT formulas use hardcoded ids while relative PIVOTS
     * formulas use the position
     *
     * e.g.
     * The following absolute formula
     *      `PIVOT("1","probability","product_id","37","bar","110")`
     * is converted to
     *      `PIVOT("1","probability","product_id",PIVOT.POSITION("1","product_id",0),"bar","110")`
     *
     * @param {Object} ast
     * @returns {Object}
     */
    _absoluteToRelative(ast) {
        switch (ast.type) {
            case "FUNCALL":
                switch (ast.value) {
                    case "ODOO.PIVOT":
                        return this._pivot_absoluteToRelative(ast);
                    case "ODOO.PIVOT.HEADER":
                        return this._pivotHeader_absoluteToRelative(ast);
                    default:
                        return Object.assign({}, ast, {
                            args: ast.args.map((child) => this._absoluteToRelative(child)),
                        });
                }
            case "UNARY_OPERATION":
                return Object.assign({}, ast, {
                    operand: this._absoluteToRelative(ast.operand),
                });
            case "BIN_OPERATION":
                return Object.assign({}, ast, {
                    right: this._absoluteToRelative(ast.right),
                    left: this._absoluteToRelative(ast.left),
                });
        }
        return ast;
    }

    /**
     * Convert a PIVOT.POSITION function AST to an absolute AST
     *
     * @see _relativeToAbsolute
     * @param {Object} ast
     * @returns {Object}
     */
    _pivotPositionToAbsolute(ast) {
        const [pivotIdAst, fieldAst, positionAst] = ast.args;
        const pivotId = pivotIdAst.value;
        const fieldName = fieldAst.value;
        const position = positionAst.value;
        const values = this.getters.getPivotGroupByValues(pivotId, fieldName);
        const id = values[position - 1];
        return {
            value: id ? `${id}` : `"#IDNOTFOUND"`,
            type: id ? "STRING" : "UNKNOWN",
        };
    }
    /**
     * Convert an absolute PIVOT.HEADER function AST to a relative AST
     *
     * @see _absoluteToRelative
     * @param {Object} ast
     * @returns {Object}
     */
    _pivotHeader_absoluteToRelative(ast) {
        ast = Object.assign({}, ast);
        const [pivotIdAst, ...domainAsts] = ast.args;
        if (pivotIdAst.type !== "STRING" && pivotIdAst.type !== "NUMBER") {
            return ast;
        }
        ast.args = [pivotIdAst, ...this._domainToRelative(pivotIdAst, domainAsts)];
        return ast;
    }
    /**
     * Convert an absolute PIVOT function AST to a relative AST
     *
     * @see _absoluteToRelative
     * @param {Object} ast
     * @returns {Object}
     */
    _pivot_absoluteToRelative(ast) {
        ast = Object.assign({}, ast);
        const [pivotIdAst, measureAst, ...domainAsts] = ast.args;
        if (pivotIdAst.type !== "STRING" && pivotIdAst.type !== "NUMBER") {
            return ast;
        }
        ast.args = [pivotIdAst, measureAst, ...this._domainToRelative(pivotIdAst, domainAsts)];
        return ast;
    }

    /**
     * Convert a pivot domain with hardcoded ids to a relative
     * domain with positions instead. Each domain element is
     * represented as an AST.
     *
     * e.g. (ignoring AST representation for simplicity)
     * The following domain
     *      "product_id", "37", "stage_id", "4"
     * is converted to
     *      "product_id", PIVOT.POSITION("#pivotId", "product_id", 15), "stage_id", PIVOT.POSITION("#pivotId", "stage_id", 3)
     *
     * @param {Object} pivotIdAst
     * @param {Object} domainAsts
     * @returns {Array<Object>}
     */
    _domainToRelative(pivotIdAst, domainAsts) {
        let relativeDomain = [];
        for (let i = 0; i <= domainAsts.length - 1; i += 2) {
            const fieldAst = domainAsts[i];
            const valueAst = domainAsts[i + 1];
            const pivotId = pivotIdAst.value;
            const fieldName = fieldAst.value;
            if (
                this._isAbsolute(pivotId, fieldName) &&
                fieldAst.type === "STRING" &&
                ["STRING", "NUMBER"].includes(valueAst.type)
            ) {
                const id = valueAst.value;
                const values = this.getters.getPivotGroupByValues(pivotId, fieldName);
                const index = values.map((val) => val.toString()).indexOf(id.toString());
                relativeDomain = relativeDomain.concat([
                    fieldAst,
                    {
                        type: "FUNCALL",
                        value: "ODOO.PIVOT.POSITION",
                        args: [pivotIdAst, fieldAst, { type: "NUMBER", value: index + 1 }],
                    },
                ]);
            } else {
                relativeDomain = relativeDomain.concat([fieldAst, valueAst]);
            }
        }
        return relativeDomain;
    }

    _isAbsolute(pivotId, fieldName) {
        const field = this.getters.getPivotDataSource(pivotId).getField(fieldName.split(":")[0]);
        return field && field.type === "many2one";
    }

    /**
     * Remove pivot formulas with invalid ids.
     * i.e. pivot formulas containing "#IDNOTFOUND".
     *
     * Rows where all pivot formulas are invalid are removed, even
     * if there are others non-empty cells.
     * Invalid formulas next to valid ones (in the same row) are simply removed.
     */
    _removeInvalidPivotRows() {
        for (const sheetId of this.getters.getSheetIds()) {
            const invalidRows = [];

            for (let rowIndex = 0; rowIndex < this.getters.getNumberRows(sheetId); rowIndex++) {
                const cellIds = Object.values(this.getters.getRowCells(sheetId, rowIndex));
                const [valid, invalid] = cellIds
                    .map((id) => this.getters.getCellById(id))
                    .filter((cell) => cell.isFormula && /^\s*=.*PIVOT/.test(cell.content))
                    .reduce(
                        ([valid, invalid], cell) => {
                            const isInvalid = /^\s*=.*PIVOT(\.HEADER)?.*#IDNOTFOUND/.test(
                                cell.content
                            );
                            return [
                                isInvalid ? valid : valid + 1,
                                isInvalid ? invalid + 1 : invalid,
                            ];
                        },
                        [0, 0]
                    );
                if (invalid > 0 && valid === 0) {
                    invalidRows.push(rowIndex);
                }
            }
            this.dispatch("REMOVE_COLUMNS_ROWS", {
                dimension: "ROW",
                elements: invalidRows,
                sheetId,
            });
        }
        this._convertFormulas(this._getCells(/^\s*=.*PIVOT.*#IDNOTFOUND/), () => null);
    }
}

PivotTemplatePlugin.getters = [];

featurePluginRegistry.add("PivotTemplate", PivotTemplatePlugin);
