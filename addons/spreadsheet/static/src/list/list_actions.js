/** @odoo-module */
// @ts-check

import { astToFormula } from "@odoo/o-spreadsheet";
import { getFirstListFunction, getNumberOfListFormulas } from "./list_helpers";
import { navigateTo } from "../actions/helpers";

/**
 * @param {import("@odoo/o-spreadsheet").CellPosition} position
 * @param {import("@spreadsheet").SpreadsheetChildEnv} env
 * @returns {Promise<void>}
 */
export const SEE_RECORD_LIST = async (position, env) => {
    const cell = env.model.getters.getCell(position);
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
    const index = evaluatedArgs[1];
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
        { viewType: "form" }
    );
};

/**
 * @param {import("@odoo/o-spreadsheet").CellPosition} position
 * @param {import("@spreadsheet").OdooGetters} getters
 * @returns {boolean}
 */
export const SEE_RECORD_LIST_VISIBLE = (position, getters) => {
    const evaluatedCell = getters.getEvaluatedCell(position);
    const cell = getters.getCell(position);
    return (
        evaluatedCell.type !== "empty" &&
        evaluatedCell.type !== "error" &&
        evaluatedCell.value !== "" &&
        cell &&
        cell.isFormula &&
        getNumberOfListFormulas(cell.compiledFormula.tokens) === 1 &&
        getFirstListFunction(cell.compiledFormula.tokens).functionName === "ODOO.LIST"
    );
};
