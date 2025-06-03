// @ts-check

import { astToFormula, helpers } from "@odoo/o-spreadsheet";
import { getFirstListFunction, getNumberOfListFormulas } from "./list_helpers";
import { navigateTo } from "../actions/helpers";

const { isMatrix } = helpers;

/**
 * @param {import("@odoo/o-spreadsheet").CellPosition} position
 * @param {import("@spreadsheet").SpreadsheetChildEnv} env
 * @param {boolean} newWindow
 * @returns {Promise<void>}
 */
export const SEE_RECORD_LIST = async (position, env, newWindow) => {
    position = env.model.getters.getEvaluatedCell(position).origin ?? position;
    const cell = env.model.getters.getCorrespondingFormulaCell(position);
    const sheetId = position.sheetId;
    if (!cell || !cell.isFormula) {
        return;
    }
    const { args } = getFirstListFunction(cell.compiledFormula.tokens);
    const evaluatedArgs = args
        .map(astToFormula)
        .map((arg) => env.model.getters.evaluateFormula(sheetId, arg));
    const listId = env.model.getters.getListIdFromPosition(position);
    const { model, actionXmlId, context } = env.model.getters.getListDefinition(listId);
    const dataSource = await env.model.getters.getAsyncListDataSource(listId);
    let index = evaluatedArgs[1];
    if (isMatrix(index)) {
        const mainPosition = env.model.getters.getCellPosition(cell.id);
        const rowOffset = position.row - mainPosition.row;
        const colOffset = position.col - mainPosition.col;
        index = index[colOffset][rowOffset];
    }

    if (typeof index !== "number") {
        return;
    }
    const recordId = dataSource.getIdFromPosition(index - 1);
    if (!recordId) {
        return;
    }
    await navigateTo(
        env,
        actionXmlId,
        {
            type: "ir.actions.act_window",
            res_model: model,
            res_id: recordId,
            views: [[false, "form"]],
            context,
        },
        { viewType: "form", newWindow }
    );
};

/**
 * @param {import("@odoo/o-spreadsheet").CellPosition} position
 * @param {import("@spreadsheet").OdooGetters} getters
 * @returns {boolean}
 */
export const SEE_RECORD_LIST_VISIBLE = (position, getters) => {
    const evaluatedCell = getters.getEvaluatedCell(position);
    position = evaluatedCell.origin ?? position;
    const cell = getters.getCorrespondingFormulaCell(position);
    return !!(
        evaluatedCell.type !== "empty" &&
        evaluatedCell.type !== "error" &&
        evaluatedCell.value !== "" &&
        cell &&
        cell.isFormula &&
        getNumberOfListFormulas(cell.compiledFormula.tokens) === 1 &&
        getFirstListFunction(cell.compiledFormula.tokens).functionName === "ODOO.LIST"
    );
};
