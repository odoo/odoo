// @ts-check

/**
 * @typedef {import("@odoo/o-spreadsheet").CellPosition} CellPosition
 * @typedef {import("@odoo/o-spreadsheet").CompiledFormula} CompiledFormula
 * @typedef {import("@odoo/o-spreadsheet").CoreGetters} CoreGetters
 * @typedef {import("@spreadsheet").OdooGetters} OdooGetters
 * @typedef  {import("../helpers/odoo_functions_helpers").OdooFunctionDescription} OdooFunctionDescription
 * */

const ALL_LIST_FUNCTIONS = ["ODOO.LIST", "ODOO.LIST.HEADER", "ODOO.LIST.VALUE"];
/**
 * Parse a spreadsheet formula and detect the number of LIST functions that are
 * present in the given formula.
 *
 * @param {CompiledFormula} compiledFormula
 *
 * @returns {boolean}
 */
export function hasListFormula(compiledFormula) {
    return ALL_LIST_FUNCTIONS.some((funcName) => compiledFormula.usesSymbol(funcName));
}

/**
 * Get the first List function description of the given formula.
 *
 * @param {CompiledFormula} compiledFormula
 * @param {CoreGetters} getters
 *
 * @returns {OdooFunctionDescription|undefined}
 */
export function getFirstListFunction(compiledFormula, getters) {
    return compiledFormula.getFunctionsFromTokens(ALL_LIST_FUNCTIONS, getters)[0];
}

export function getListFunctions(compiledFormula, getters) {
    return compiledFormula.getFunctionsFromTokens(ALL_LIST_FUNCTIONS, getters);
}

export function addListDependencies(evalContext, listId, columns) {
    const dependencies = [];
    for (const column of columns) {
        if (column.computedBy) {
            dependencies.push(
                ...evalContext.getters.getListCompiledColumnDependencies(listId, column.name)
            );
        }
    }
    const originPosition = evalContext.__originCellPosition;
    if (originPosition && dependencies.length) {
        // The following line is used to reset the dependencies of the cell, to avoid
        // keeping dependencies from previous evaluation of the LIST formula (i.e.
        // in case the reference has been changed).
        evalContext.updateDependencies?.(originPosition);
        evalContext.addDependencies?.(originPosition, dependencies);
    }
}

/**
 * Get the static formula of a cell of a dynamic list (=ODOO.LIST), e.g.
 * =ODOO.LIST.HEADER(1,"name") for the header row and
 * =ODOO.LIST.VALUE(1,3,"name") for the third record.
 *
 * @param {CellPosition} position
 * @param {OdooGetters} getters
 *
 * @returns {string}
 */
export function getListStaticFormula(position, getters) {
    const listId = getters.getListIdFromPosition(position);
    const spreader = getters.getArrayFormulaSpreadingOn(position);
    const columns = getters.getListDefinition(listId).columns.filter((col) => !col.hidden);
    const fieldName = columns[position.col - spreader.col].name;
    const index = position.row - spreader.row;
    return index === 0
        ? `=ODOO.LIST.HEADER(${listId},"${fieldName}")`
        : `=ODOO.LIST.VALUE(${listId},${index},"${fieldName}")`;
}
